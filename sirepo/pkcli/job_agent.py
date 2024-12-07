"""Agent for managing the execution of jobs.

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern import pkconfig
from pykern import pkio
from pykern import pkjson
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdlog, pkdp, pkdexc, pkdc, pkdformat
from sirepo import job
from sirepo.template import template_common
import copy
import datetime
import os
import re
import signal
import sirepo.const
import sirepo.feature_config
import sirepo.modules
import sirepo.nersc
import sirepo.tornado
import sirepo.util
import socket
import subprocess
import time
import tornado.gen
import tornado.ioloop
import tornado.iostream
import tornado.locks
import tornado.netutil
import tornado.process
import tornado.websocket


#: Long enough for job_cmd to write result in run_dir
_TERMINATE_SECS = 3

#: How often to poll in loop()
_RETRY_SECS = 1

#: Reasonable over the Internet connection
_CONNECT_SECS = 10

_IN_FILE = "in-{}.json"

_PID_FILE = "job_agent.pid"

_SBATCH_STATUS_FILE = "sbatch_status.json"

_MIN_POLL_SECS = 5

_MAX_SCONTROL_TRIES = 10

_cfg = None

_DEV_PYTHON_PATH = ":".join(
    str(sirepo.const.DEV_SRC_RADIASOFT_DIR.join(p)) for p in ("sirepo", "pykern")
)


def start():
    # TODO(robnagler) commands need their own init hook like the server has
    global _cfg

    _cfg = pkconfig.init(
        agent_id=pkconfig.Required(str, "id of this agent"),
        # POSIT: same as job_driver.DriverBase._agent_env
        dev_source_dirs=(
            pkconfig.in_dev_mode(),
            bool,
            f"set PYTHONPATH={_DEV_PYTHON_PATH}",
        ),
        fastcgi_sock_dir=(
            pkio.py_path("/tmp"),
            pkio.py_path,
            "directory of fastcfgi socket, must be less than 50 chars",
        ),
        start_delay=(0, pkconfig.parse_seconds, "delay startup in internal_test mode"),
        global_resources_server_token=pkconfig.Required(
            str,
            "credential for global resources server",
        ),
        global_resources_server_uri=pkconfig.Required(
            str,
            "how to connect to global resources",
        ),
        sim_db_file_server_token=pkconfig.Required(
            str,
            "credential for sim db files",
        ),
        sim_db_file_server_uri=pkconfig.Required(
            str,
            "how to connect to sim db files",
        ),
        supervisor_uri=pkconfig.Required(
            str,
            "how to connect to the supervisor",
        ),
    )
    pkdlog("{}", _cfg)
    if pkconfig.channel_in_internal_test() and _cfg.start_delay:
        pkdlog("start_delay={}", _cfg.start_delay)
        # Not asyncio.sleep: delay to startup tornado for testing
        time.sleep(_cfg.start_delay)
    i = tornado.ioloop.IOLoop.current()
    d = _Dispatcher()

    def s(*args):
        return i.add_callback_from_signal(_terminate, d)

    signal.signal(signal.SIGTERM, s)
    signal.signal(signal.SIGINT, s)
    i.spawn_callback(d.loop)
    i.start()


def start_sbatch():
    def get_host():
        h = socket.gethostname()
        if "." not in h:
            h = socket.getfqdn()
        return h

    def kill_agent(pid_file):
        if get_host() == pid_file.host:
            os.kill(pid_file.pid, signal.SIGKILL)
        else:
            try:
                subprocess.run(
                    ("ssh", pid_file.host, "kill", "-KILL", str(pid_file.pid)),
                    capture_output=True,
                    text=True,
                ).check_returncode()
            except subprocess.CalledProcessError as e:
                if "({}) - No such process".format(pid_file.pid) not in e.stderr:
                    pkdlog(
                        "cmd={cmd} returncode={returncode} stderr={stderr}", **vars(e)
                    )

    f = None
    try:
        f = pkjson.load_any(pkio.py_path(_PID_FILE))
    except Exception as e:
        if not pkio.exception_is_not_found(e):
            pkdlog("error={} stack={}", e, pkdexc())
    try:
        if f:
            kill_agent(f)
    except Exception as e:
        pkdlog("error={} stack={}", e, pkdexc())
    pkjson.dump_pretty(
        PKDict(
            host=get_host(),
            pid=os.getpid(),
        ),
        _PID_FILE,
    )
    try:
        start()
    finally:
        # TODO(robnagler) https://github.com/radiasoft/sirepo/issues/2195
        pkio.unchecked_remove(_PID_FILE)


def _assert_run_dir_exists(run_dir):
    if not run_dir.exists():
        raise _RunDirNotFound()


class _Dispatcher(PKDict):
    def __init__(self):
        super().__init__(
            cmds=[],
            fastcgi_cmd=None,
            fastcgi_error_count=0,
        )

    def fastcgi_destroy(self):
        self._fastcgi_file and pkio.unchecked_remove(self._fastcgi_file)
        self._fastcgi_file = None
        self.fastcgi_cmd = None

    def format_canceled(self, msg):
        return self.format_op(msg, job.OP_OK, reply=PKDict(state=job.CANCELED))

    def format_op(self, msg, op_name, **kwargs):
        if msg:
            kwargs["opId"] = msg.get("opId")
        return _OpMsg(agentId=_cfg.agent_id, opName=op_name).pksetdefault(**kwargs)

    async def job_cmd_reply(self, msg, op_name, text):
        try:
            r = pkjson.load_any(text)
        except Exception:
            op_name = job.OP_ERROR
            r = PKDict(
                state=job.ERROR,
                error=f"unable to parse job_cmd output",
                stdout=text,
            )
        try:
            k = PKDict(reply=r)
            if msg.opName == job.OP_RUN:
                # Even on errors, we force the op_name
                op_name = job.OP_RUN_STATUS_UPDATE
                k.computeJid = msg.computeJid
                k.computeJobSerial = msg.computeJobSerial
            await self.send(self.format_op(msg, op_name, **k))
        except Exception as e:
            pkdlog("reply={} error={} stack={}", r, e, pkdexc())
            # something is really wrong, because format_op is messed up
            raise

    async def loop(self):
        while True:
            self._websocket = None
            try:
                self._websocket = await tornado.websocket.websocket_connect(
                    tornado.httpclient.HTTPRequest(
                        connect_timeout=_CONNECT_SECS,
                        url=_cfg.supervisor_uri,
                        validate_cert=job.cfg().verify_tls,
                    ),
                    max_message_size=job.cfg().max_message_bytes,
                    ping_interval=job.cfg().ping_interval_secs,
                    ping_timeout=job.cfg().ping_timeout_secs,
                )
                s = self.format_op(None, job.OP_ALIVE)
                while True:
                    if s and not await self.send(s):
                        break
                    r = await self._websocket.read_message()
                    if r is None:
                        pkdlog(
                            "websocket closed in response to len={} send={}",
                            s and len(s),
                            s,
                        )
                        raise tornado.iostream.StreamClosedError()
                    s = await self._op(r)
            except Exception as e:
                if not isinstance(e, tornado.iostream.StreamClosedError):
                    pkdlog("retry websocket; error={} stack={}", e, pkdexc())
                await tornado.gen.sleep(_RETRY_SECS)
            finally:
                if self._websocket:
                    self._websocket.close()

    async def send(self, msg):
        if not self._websocket:
            return False
        try:
            if not isinstance(msg, _OpMsg):
                raise AssertionError("expected _OpMsg type={} msg={}", type(msg), msg)
            await self._websocket.write_message(pkjson.dump_bytes(msg))
            return True
        except Exception as e:
            pkdlog("exception={} msg={} stack={}", e, msg, pkdexc())
            return False

    def terminate(self):
        try:
            x = self.cmds
            # compute_jobs are passive
            self.cmds = []
            for c in x:
                try:
                    c.destroy(terminating=True)
                except Exception as e:
                    pkdlog("cmd={} error={} stack={}", c, e, pkdexc())
            return None
        finally:
            tornado.ioloop.IOLoop.current().stop()

    def _get_cmd_type(self, msg):
        if msg.jobRunMode == job.SBATCH:
            return _SbatchRun if msg.opName == job.OP_RUN else return _SbatchCmd
        elif msg.jobCmd == "fastcgi":
            return _FastCgiCmd
        return _Cmd

    async def _cmd(self, msg, **kwargs):
        try:
            if (
                msg.opName
                in (
                    job.OP_ANALYSIS,
                    job.OP_IO,
                )
                and msg.jobCmd != "fastcgi"
            ):
                return await self._fastcgi_op(msg)
            kwargs.setdefault("send_reply", True)
            c = self._get_cmd_type(msg)(
                msg=msg, dispatcher=self, op_id=msg.opId, **kwargs
            )
        except _RunDirNotFound:
            return self.format_op(
                msg,
                job.OP_ERROR,
                reply=PKDict(runDirNotFound=True),
            )
        if msg.jobCmd == "fastcgi":
            self.fastcgi_cmd = c
        try:
            return c.start()
        except Exception as e:
            pkdlog("start exception={} stack={}", e, pkdexc())
            c.destroy()

    def _fastcgi_accept(self, connection, *args, **kwargs):
        # Impedence mismatch: _fastcgi_accept cannot be async, because
        # bind_unix_socket doesn't await the callable.
        _call_later_0(self._fastcgi_read, connection)

    async def _fastcgi_handle_error(self, msg, error, stack=None):
        async def _reply_error(msg):
            try:
                await self.send(
                    self.format_op(
                        msg,
                        job.OP_ERROR,
                        error=error,
                        reply=PKDict(
                            state=job.ERROR,
                            error="internal error",
                            fastCgiErrorCount=self.fastcgi_error_count,
                        ),
                    )
                )
            except Exception as e:
                pkdlog("msg={} error={} stack={}", msg, e, pkdexc())

        # destroy _fastcgi state first, then send replies to avoid
        # asynchronous modification of _fastcgi state.
        self.fastcgi_error_count += 1
        self._fastcgi_remove_handler()
        q = self._fastcgi_msg_q
        self._fastcgi_msg_q = None
        self.fastcgi_cmd.destroy()
        if msg:
            await _reply_error(msg)
        while q.qsize() > 0:
            await _reply_error(q.get_nowait())
            q.task_done()

    async def _fastcgi_op(self, msg):
        if msg.runDir:
            _assert_run_dir_exists(pkio.msg.runDir))
        if not self.fastcgi_cmd:
            m = copy.deepcopy(msg)
            m.jobCmd = "fastcgi"
            self._fastcgi_file = _cfg.fastcgi_sock_dir.join(
                f"sirepo_job_cmd-{_cfg.agent_id:8}.sock",
            )
            self._fastcgi_msg_q = sirepo.tornado.Queue(1)
            pkio.unchecked_remove(self._fastcgi_file)
            m.fastcgiFile = self._fastcgi_file
            # Runs in an agent's directory and chdirs to real runDirs.
            # Except in stateless_compute which doesn't interact with the db.
            m.runDir = pkio.py_path()
            # Kind of backwards, but it makes sense since we need to listen
            # so _do_fastcgi can connect
            self._fastcgi_remove_handler = tornado.netutil.add_accept_handler(
                tornado.netutil.bind_unix_socket(str(self._fastcgi_file)),
                self._fastcgi_accept,
            )
            # last thing, because of await: start fastcgi process
            await self._cmd(m, send_reply=False)
        self._fastcgi_msg_q.put_nowait(msg)
        # For better logging, msg.opId is used in format_op (reply)
        self.fastcgi_cmd.op_id = msg.opId
        return None

    async def _fastcgi_read(self, connection):
        s = None
        m = None
        try:
            s = tornado.iostream.IOStream(
                connection,
                max_buffer_size=job.cfg().max_message_bytes,
            )
            while True:
                m = await self._fastcgi_msg_q.get()
                # Avoid issues with exceptions. We don't use q.join()
                # so not an issue to call before work is done.
                self._fastcgi_msg_q.task_done()
                await s.write(pkjson.dump_bytes(m) + b"\n")
                await self.job_cmd_reply(
                    m,
                    job.OP_OK,
                    await s.read_until(b"\n", job.cfg().max_message_bytes),
                )
        except Exception as e:
            pkdlog("msg={} error={} stack={}", m, e, pkdexc())
            # If self.fastcgi_cmd is None we initiated the kill so not an error
            if not self.fastcgi_cmd:
                return
            await self._fastcgi_handle_error(m, e, pkdexc())
        finally:
            if s:
                s.close()

    async def _op(self, msg):
        m = None
        try:
            m = pkjson.load_any(msg)
            pkdlog(
                "opName={} o={:.4} runDir={}", m.opName, m.get("opId"), m.get("runDir")
            )
            pkdc("m={}", m)
            return await getattr(self, "_op_" + m.opName)(m)
        except Exception as e:
            err = "exception=" + str(e)
            stack = pkdexc()
            pkdlog(
                "opName={} o={:.4} exception={} stack={}",
                m and m.get("opName"),
                m and m.get("opId"),
                e,
                stack,
            )
            return self.format_op(m, job.OP_ERROR, error=err, stack=stack)

    async def _op_analysis(self, msg):
        return await self._cmd(msg)

    async def _op_begin_session(self, msg):
        return self.format_op(msg, job.OP_OK, reply=PKDict(awake=True))

    async def _op_cancel(self, msg):
        def _matches():
            return set(c for c in self.cmds if c.op_id == msg.opId or c.jid == msg.jid)

        for c in _matches():
            c.cancel_request()
        return self.format_canceled(msg)

    async def _op_io(self, msg):
        return await self._cmd(msg)

    async def _op_kill(self, msg):
        self.terminate()
        return None

    async def _op_run(self, msg):
        return await self._cmd(msg)

    async def _op_run_status(self, msg):
        for c in list(self.cmds):
            if not (c.jid == msg.computeJid and s := c.get("job_state")):
                continue
            if c.computeJobSerial != msg.computeJobSerial:
                return self.format_op(
                    msg,
                    job.OP_ERROR,
                    reply=PKDict(state=job.UNKNOWN, error="run_status computeJobSerial mismatch"),
                )
            return self.format_op(
                msg,
                job.OP_OK,
                reply=PKDict(state=s, computeJobSerial=msg.computeJobSerial),
            )
        if msg.jobRunMode == job.SBATCH:
            return _SbatchRunStatus.sbatch_status_request(msg=msg, dispatcher=self, op_id=msg.opId)
        return self.format_canceled(msg)

    async def _op_sbatch_login(self, msg):
        return self.format_op(msg, job.OP_OK, reply=PKDict(loginSuccess=True))


class _Cmd(PKDict):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # only certain types of commands have runDir
        if self.msg.get("runDir"):
            self.run_dir = pkio.py_path(self.msg.runDir)
            if self.msg.opName == job.OP_RUN:
                self.computeJobSerial = self.msg.computeJobSerial
                self.job_state = job.PENDING
                pkio.unchecked_remove(self.run_dir)
                pkio.mkdir_parent(self.run_dir)
            else:
                _assert_run_dir_exists(self.run_dir)
        else:
            # POSIT: same as fast_cgi
            # Use agent's runDir.
            self.run_dir = pkio.py_path()
        self._destroying = False
        self._in_file = self._create_in_file()
        self._process = _Process(self)
        self._start_time = int(time.time())
        self._terminating = False
        self.jid = self.msg.computeJid
        self._uid = job.split_jid(jid=self.jid).uid
        self.dispatcher.cmds.append(self)

    def cancel_request(self):
        if self.job:
            await self.job.cancel_request()
        self.destroy()

    def destroy(self, terminating=False):
        if self._destroying:
            return
        self._destroying = True
        self._terminating = terminating
        if self.job:
            self.job.destroy()
        if "_in_file" in self:
            pkio.unchecked_remove(self.pkdel("_in_file"))
        self._process.kill()
        try:
            self.dispatcher.cmds.remove(self)
        except ValueError:
            pass

    def format_op(self, **kwargs):
        return self.dispatcher.format_op(
            **PKDict(kwargs).pksetdefault(
                op_name=job.ERROR,
                msg=self.msg,
            ),
        )

    def format_op_reply(self, **reply_kwargs):
        return self.dispatcher.format_op(
            op_name=job.OK,
            msg=self.msg,
            reply=PKDict(reply_kwargs),
        )

    def job_cmd_cmd(self):
        return ("sirepo", "job_cmd", self._in_file)

    def job_cmd_cmd_stdin_env(self):
        return job.agent_cmd_stdin_env(
            cmd=self.job_cmd_cmd(),
            env=self.job_cmd_env(),
            source_bashrc=self.job_cmd_source_bashrc(),
            uid=self._uid,
        )

    def job_cmd_env(self, env=None):
        return job.agent_env(
            env=(env or PKDict()).pksetdefault(
                SIREPO_GLOBAL_RESOURCES_SERVER_TOKEN=_cfg.global_resources_server_token,
                SIREPO_GLOBAL_RESOURCES_SERVER_URI=_cfg.global_resources_server_uri,
                SIREPO_MPI_CORES=self.msg.get("mpiCores", 1),
                SIREPO_SIM_DB_FILE_SERVER_TOKEN=_cfg.sim_db_file_server_token,
                SIREPO_SIM_DB_FILE_SERVER_URI=_cfg.sim_db_file_server_uri,
            ),
            uid=self._uid,
        )

    def job_cmd_source_bashrc(self):
        if sirepo.feature_config.cfg().trust_sh_env:
            return ""
        return "source $HOME/.bashrc"

    async def on_stderr_read(self, text):
        try:
            await self.dispatcher.send(
                self.format_op(
                    msg=None,
                    op_name=job.OP_JOB_CMD_STDERR,
                    stderr=text.decode("utf-8", errors="ignore"),
                )
            )
        except Exception as exc:
            pkdlog("{} text={} error={} stack={}", self, text, exc, pkdexc())

    async def on_stdout_read(self, text):
        if self._destroying:
            return
        if not self.send_reply:
            pkdlog("{} unexpected stdout={}", self, text)
            return
        try:
            await self.dispatcher.job_cmd_reply(self.msg, job.OP_OK, text)
        except Exception as e:
            pkdlog("{} text={} error={} stack={}", self, text, e, pkdexc())

    def pkdebug_str(self):
        return pkdformat(
            "{}(a={:.4} jid={} o={:.4} job_cmd={} run_dir={})",
            self.__class__.__name__,
            _cfg.agent_id,
            self.get("jid"),
            self.get("op_id"),
            self.msg.get("jobCmd"),
            self.run_dir,
        )

    def start(self):
        r = PKDict(state=job.STATE_OK)
        try:
            self._process.start()
        except Exception as e:
            pkdlog("{} exception={} stack={}", self, e, pkdexc())
            rv = self.format_op(reply=PKDict(state=job.ERROR, error="failed to start process"))
            self.destroy()
            return rv
        _call_later_0(self._await_exit)
        if "job_state" not in self:
            return
        self.job_state = job.RUNNING
        if s := self.get("_start_time"):
            r.computeJobStart = s
        rv = self.format_op(op_name=job.OP_OK, reply=r)
        # No longer bound to an op. will just send RUN_STATUS_UPDATES
        self.op_id = None
        self.msg.opId = None
        return rv

    async def _await_exit(self):
        try:
            await self._process.exit_ready()
            e = self._process.stderr.text.decode("utf-8", errors="ignore")
            if e:
                pkdlog("{} exit={} stderr={}", self, self._process.returncode, e)
            if self._destroying:
                return
            if self._process.returncode != 0:
                await self.dispatcher.send(
                    self.format_op(
                        error=e,
                        reply=PKDict(
                            state=job.ERROR,
                            error=f"process exit={self._process.returncode} jid={self.job.jid}",
                        ),
                    )
                )

        except Exception as exc:
            pkdlog(
                "{} error={} returncode={} stack={}",
                self,
                exc,
                self._process.returncode,
                pkdexc(),
            )
            await self.dispatcher.send(
                self.format_op(
                    error=str(exc),
                    reply=PKDict(
                        state=job.ERROR,
                        error="job_agent error",
                    ),
                ),
            )
        finally:
            self.destroy()

    def _create_in_file(self):
        f = self.run_dir.join(
            _IN_FILE.format(sirepo.util.unique_key()),
        )
        pkjson.dump_pretty(self.msg, filename=f, pretty=False)
        return f

class _FastCgiCmd(_Cmd):
    def destroy(self, terminating=False):
        if self._destroying:
            return
        self.dispatcher.fastcgi_destroy()
        super().destroy(terminating=terminating)


class _OpMsg(PKDict):
    pass

class _Process(PKDict):
    def __init__(self, cmd):
        super().__init__()
        self.update(
            stderr=None,
            stdout=None,
            cmd=cmd,
            _exit=sirepo.tornado.Event(),
        )

    async def exit_ready(self):
        await self._exit.wait()
        await self.stdout.stream_closed.wait()
        await self.stderr.stream_closed.wait()

    def kill(self):
        # If the process is't started
        if "returncode" in self or "_subprocess" not in self:
            return
        p = None
        try:
            pkdlog("{}", self)
            p = self.pkdel("_subprocess").proc.pid
            os.killpg(p, signal.SIGKILL)
        except Exception as e:
            pkdlog("{} error={}", self, e)

    def pkdebug_str(self):
        return pkdformat(
            "{}(pid={} cmd={})",
            self.__class__.__name__,
            self._subprocess.proc.pid if self.get("_subprocess") else None,
            self.cmd,
        )

    def start(self):
        # SECURITY: msg must not contain agentId
        assert not self.cmd.msg.get("agentId")
        c, s, e = self.cmd.job_cmd_cmd_stdin_env()
        pkdlog("cmd={} stdin={}", c, s.read())
        s.seek(0)
        self._subprocess = tornado.process.Subprocess(
            c,
            close_fds=True,
            cwd=str(self.cmd.run_dir),
            env=e,
            start_new_session=True,
            stdin=s,
            stdout=tornado.process.Subprocess.STREAM,
            stderr=tornado.process.Subprocess.STREAM,
        )
        s.close()
        self.stdout = _ReadJsonlStream(self._subprocess.stdout, self.cmd)
        self.stderr = _ReadUntilCloseStream(self._subprocess.stderr, self.cmd)
        self._subprocess.set_exit_callback(self._on_exit)
        return self

    def _on_exit(self, returncode):
        self.returncode = returncode
        self._exit.set()


class _RunDirNotFound(Exception):
    pass


class _Stream(PKDict):
    def __init__(self, stream, cmd):
        super().__init__(
            cmd=cmd,
            stream_closed=sirepo.tornado.Event(),
            text=bytearray(),
            _stream=stream,
        )
        _call_later_0(self._begin_read_stream)

    async def _begin_read_stream(self):
        try:
            while True:
                await self._read_stream()
        except tornado.iostream.StreamClosedError as e:
            assert e.real_error is None, "real_error={}".format(e.real_error)
        finally:
            self._stream.close()
            self.stream_closed.set()

    async def _read_stream(self):
        raise NotImplementedError()


class _ReadJsonlStream(_Stream):
    def __init__(self, *args):
        self.proceed_with_read = tornado.locks.Condition()
        self.read_occurred = tornado.locks.Condition()
        super().__init__(*args)

    async def _read_stream(self):
        self.text = await self._stream.read_until(b"\n", job.cfg().max_message_bytes)
        pkdc("cmd={} stdout={}", self.cmd, self.text[:1000])
        await self.cmd.on_stdout_read(self.text)


class _ReadUntilCloseStream(_Stream):
    def __init__(self, *args):
        super().__init__(*args)

    async def _read_stream(self):
        t = await self._stream.read_bytes(
            job.cfg().max_message_bytes - len(self.text),
            partial=True,
        )
        pkdlog("cmd={} stderr={}", self.cmd, t)
        await self.cmd.on_stderr_read(t)
        l = len(self.text) + len(t)
        assert (
            l < job.cfg().max_message_bytes
        ), "len(bytes)={} greater than max_message_size={}".format(
            l,
            job.cfg().max_message_bytes,
        )
        self.text.extend(t)


class _SbatchCmd(_Cmd):
    def __init__(self, **kwargs):
        super.__init__(**kwargs)
        if "job_state" not in self:
            return
        self.pkupdate(
            _sbatch_status=PKDict(
                job_cmd_state=None,
                sbatch_id=None,
                scontrol_state=None,
                start_time=None,
            ),
            _sbatch_status_cb=None,
            _sbatch_status_file=self.run_dir.join(_SBATCH_STATUS_FILE),
            _scontrol_tries=0,
        )
        self.pkdel("_start_time")

    def job_cmd_cmd_stdin_env(self, *args, **kwargs):
        c, s, e = super().job_cmd_cmd_stdin_env()
        if self.msg.get("shifterImage"):
            c = (
                "shifter",
                "--entrypoint",
                f"--image={self.msg.shifterImage}",
                "/bin/bash",
                "--norc",
                "--noprofile",
                "-l",
            )
        return c, s, e

    def job_cmd_env(self):
        # POSIT: sirepo.mpi cfg sentinel for running in slurm
        e = PKDict(SIREPO_MPI_IN_SLURM=1)
        if _cfg.dev_source_dirs:
            e.PYTHONPATH = _DEV_PYTHON_PATH
        return super().job_cmd_env(e)


    def job_cmd_source_bashrc(self):
        if not self.msg.get("shifterImage"):
            return super().job_cmd_source_bashrc()
        return ""

    def _sbatch_status_update(self, **kwargs):
        p = self._sbatch_status.copy()
        self._sbatch_status.pkupdate(kwargs)
        if p == self._sbatch_status:
            return True
        try:
            pkio.atomic_write(
                self._sbatch_status_file, pkjson.dump_pretty(self._sbatch_status)
            )
            return True
        except Exception as e:
            # The simulation directory might get deleted out from
            # under this process or some other error.
            pkdlog("error writing file={} exception={} stack={}", self._sbatch_status_file, e, pkdexc())
            return False


class _SbatchRun(_SbatchCmd):

    def start(self):
        # process could be here
        p = subprocess.run(
            ("sbatch", self._sbatch_script()),
            close_fds=True,
            cwd=str(self.run_dir),
            capture_output=True,
            text=True,
        )
        m = re.search(r"Submitted batch job (\d+)", p.stdout)
        # Failure might be out of hours or batch system down
        if m:
            if self._sbatch_status_update(sbatch_id=m.group(1)):
                rv = self.format_op(op_name=job.OP_OK, reply=PKDict(state=job.OK))
            else:
                rv = self.format_op(error="unable to write sbatch state file")
                #TODO(robnagler) need to cancel job, because no way to attach
        else:
            pkdlog("exit={} stdout={} stderr={}", p.returncode, p.stdout, p.stderr)
            rv = self.format_op(
                error=f"error submitting sbatch job error={p.stderr}",
            )
        if rv.opName == job.OP_OK:
            rv = _SbatchRunStatus.sbatch_status_request(
                msg=self.msg.copy().pkupdate(opId=None),
                dispatcher=self.dispatcher,
                op_id=None,
            )
            if rv.opName == job.OP_OK and rv.reply.state == job.UNKNOWN:
                # sbatch_status_request replies UNKNOWN when normal state
                rv = self.format_op_reply(state=job.OK)
        self.destroy()
        return rv

    def _sbatch_script(self):
        def _nodes_tasks():
            return f"#SBATCH --nodes={self.msg.sbatchNodes}" if self.msg.get("sbatchNodes") else "#SBATCH --cpus-per-task={self.msg.sbatchCores}"

        def _prepare_simulation():
            return """python <<'EOF'
import sirepo.simulation_db
import pykern.pkjson

# returns the python command, but too complicated to couple
simulation_db.prepare_simulation(
    # python serialization does not work
    pykern.pkjson.load_any('''{pkjson.dump_pretty(self.msg.data)}''',
    'self.msg.runDir',
)
EOF"""
        def _shifter_cmd():
            return "--cpu-bind=cores shifter --entrypoint" if self.msg.get("shifterImage") else ""

        def _shifter_header():
            # POSIT: job_api has validated values
            if ! self.msg.get("shifterImage"):
                return ""
            return f"""#SBATCH --image={i}
#SBATCH --constraint=cpu
#SBATCH --qos={self.msg.sbatchQueue}
#SBATCH --tasks-per-node={self.msg.tasksPerNode}
{sirepo.nersc.sbatch_project_option(self.msg.sbatchProject)}"""

        def _time():
            return str(
                datetime.timedelta(
                    seconds=int(
                        datetime.timedelta(
                            hours=float(self.msg.sbatchHours)
                        ).total_seconds(),
                    ),
                )
            )


        f = self.run_dir.join(self.jid + ".sbatch")
        f.write(
            f"""#!/bin/bash
#SBATCH --error={template_common.RUN_LOG}
#SBATCH --output={template_common.RUN_LOG}
#SBATCH --time={_time()}
{_nodes_tasks()}
{_shifter_header()}
{self.job_cmd_env()}
{self.job_cmd_source_bashrc()}
{_prepare_simulation()}
# POSIT: same as return value of prepare_simulation
exec srun {_shifter_cmd()} python {template_common.PARAMETERS_PYTHON_FILE}
"""
        )
        return f

class _SbatchRunStatus(_SbatchCmd):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.msg.jobCmd = "sbatch_parallel_status"

    @classmethod
    def sbatch_status_request(cls, **kwargs):
        def _check_status():
            if e := self._sbatch_status_file_read():
                return e
            if self._sbatch_scontrol():
                return None
            pkdlog("{} no scontrol state so assuming canceled sbatch_id=", self._sbatch_status.sbatch_id)
            e = job.CANCELED
            self._sbatch_status_update(job_cmd_state=e)
            return e

        self = cls(**kwargs)
        if s := _check_status():
            self.destroy()
            return self.format_op_reply(state=s)
        rjn need to check COMPLETED to write final parallel status
        rjn set start_time if not set. maybe totally wrong if process is no longer running
        # running, possibly completed, but needs to write parallel status
        self.start()
        # can't answer the question yet
        # POSIT: expected by _SbatchRun.start
        return self.format_op_reply(state=job.UNKNOWN)

    def start(self):
        self._sbatch_status_cb = tornado.ioloop.PeriodicCallback(
            self._sbatch_poll_scontrol,
            min(_MIN_POLL_SECS, self.msg.runStatusPollSeconds * 1000),
        )
        self._sbatch_status_cb.start()
        # So happens right away
        _call_later_0(self._sbatch_poll_scontrol)

    def _sbatch_scontrol(self):
        def _show_job():
            p = subprocess.run(
                ("scontrol", "show", "job", self._sbatch_status.sbatch_id),
                cwd=str(self.run_dir),
                close_fds=True,
                capture_output=True,
                text=True,
            )
            if p.returncode != 0:
                pkdlog(
                    "{} scontrol error exit={} sbatch={} stderr={} stdout={}",
                    self,
                    p.returncode,
                    self._sbatch_status.sbatch_id,
                    p.stderr,
                    p.stdout,
                )
                return None
            r = re.search(r"(?<=JobState=)(\S+)(?= Reason)", p.stdout)
            if not r:
                pkdlog(
                    "{} failed to find JobState in stderr={} stdout={}",
                    self,
                    p.stderr,
                    p.stdout,
                )
                return None
            return r.group(1)

        if not (s := _show_job()):
            return None
        if s in ("PENDING", "CONFIGURING"):
            return job.PENDING
        if s in ("COMPLETING", "RUNNING"):
            return job.RUNNING
        if s == "COMPLETED":
            return s
        if s in ("CANCELLED"):
            return job.CANCELED
        pkdlog(
            "{} sbatch_id={} unexpected scontrol_state={}", self, self._sbatch_status.sbatch_id, s)
        return job.ERROR


    async def _sbatch_poll_scontrol(self):
        def _state(s):
            if not (s := _scontrol()):
                self._scontrol_tries += 1
                return job.ERROR if self._scontrol_tries > _MAX_SCONTROL_TRIES else None
            self._scontrol_tries = 0
            if self._sbatch_status.scontrol_state in ("PENDING", "CONFIGURING"):
                return job.PENDING
            if self._sbatch_status.scontrol_state in ("CANCELLED"):
                return job.CANCELED
            if not self._sbatch_running.is_set():
                self._start_time = int(time.time())
                self._sbatch_running.set()
            if self._sbatch_status.scontrol_state in ("COMPLETING", "RUNNING"):
                return job.RUNNING
            if c := self._sbatch_status.scontrol_state == "COMPLETED":
                self._sbatch_status_update(
                    job_cmd_state=job.JOB_CMD_STATE_SBATCH_RUN_STATUS_STOP,
                )
                # Do not reply; final parallel status will reply.
                return None
            return job.ERROR

        if self._destroying:
            return
        if s := _state(_scontrol()):
            e = None
            if s == job.ERROR:
                e = f"unexpected scontrol_state={self._sbatch_status.scontrol_state}"
                pkdlog(
                    "{} sbatch_id={} {}", self, self._sbatch_status.sbatch_id, e,
                )
            await _reply_and_maybe_destroy(s, error=e)

    def _sbatch_status_file_read(self):
        if not self._sbatch_status_file.exists():
            pkdlog("missing sbatch status file={}", self._sbatch_status_file)
            return job.CANCELED
        c = None
        try:
            c = self._sbatch_status_file.read()
            s = pkjson.load_any(c)
        except Exception as e:
            pkdlog("file={} exception={} contents={}", self._sbatch_status_file, e, c)
            pkio.unchecked_remove(self._sbatch_status_file)
            return job.CANCELED
        if not s.get("sbatch_id") or not s.get("job_cmd_state"):
            pkdlog("invalid sbatch_status={} file={}", s, self._sbatch_status_file)
            return job.CANCELED
        if s.job_cmd_state in job.EXIT_STATUSES:
            return s.job_cmd_state
        self._sbatch_status = s
        return None

    def destroy(self, terminating=False):
        def _scancel(sbatch_id):
            pkdlog("sbatch_id={}", sbatch_id)
            p = subprocess.run(
                ("scancel", "--full", "--quiet", sbatch_id),
                close_fds=True,
                cwd=str(self.run_dir),
                capture_output=True,
                text=True,
            )
            if p.returncode != 0:
                pkdlog(
                    "{} cancel error exit={} sbatch={} stderr={} stdout={}",
                    self,
                    p.returncode,
                    sbatch_id,
                    p.stderr,
                    p.stdout,
                )

        if self._destroying:
            return
        self._destroying = True
        self._terminating = terminating
        if self._sbatch_status_cb:
            self._sbatch_status_cb.stop()
            self._sbatch_status_cb = None
        self._sbatch_running.set()
        if (
            self._sbatch_status.job_cmd_state not in job.JOB_CMD_STATE_EXITS
            and self._sbatch_status.sbatch_id
            and not self._terminating
        ):
            self._sbatch_status_update(job_cmd_state=job.CANCELED)
            _scancel(self._sbatch_status.sbatch_id)
        super().destroy(terminating=terminating)


def _call_later_0(*args, **kwargs):
    return tornado.ioloop.IOLoop.current().call_later(0, *args, **kwargs)


def _terminate(dispatcher):
    dispatcher.terminate()
    # just in case isn't removed by start_sbatch
    pkio.unchecked_remove(_PID_FILE)
