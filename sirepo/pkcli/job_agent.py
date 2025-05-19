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
_LOOP_RETRY_SECS = 1

#: How many retries before the agent kills itself
_MAX_LOOP_RETRY = 10


#: Reasonable over the Internet connection
_CONNECT_SECS = 10

_IN_FILE = "in-{}.json"

_PID_FILE = "job_agent.pid"

_SBATCH_STATUS_FILE = "sbatch_status.json"

_MIN_SBATCH_POLL_SECS = 5

_MAX_SBATCH_QUERY_TRIES = 5

_cfg = None

_DEV_PYTHON_PATH = ":".join(
    str(pkio.py_path(sirepo.const.DEV_SRC_RADIASOFT_DIR).join(p))
    for p in ("sirepo", "pykern")
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
    def _get_host():
        h = socket.gethostname()
        if "." not in h:
            h = socket.getfqdn()
        return h

    def _kill_agent(pid_file):
        pkio.unchecked_remove(_PID_FILE)
        if _get_host() == pid_file.host:
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

    def _read_pid_file():
        try:
            rv = pkjson.load_any(pkio.py_path(_PID_FILE))
            if "host" in rv and "pid" in rv:
                return rv
        except Exception as e:
            if not pkio.exception_is_not_found(e):
                pkdlog("file={} error={} stack={}", e, pkdexc())
        return None

    def _remove_own_pid_file(info):
        try:
            if (f := _read_pid_file()) and f.host == info.host and f.pid == info.pid:
                # race condition but very small so probably ok
                pkio.unchecked_remove(_PID_FILE)
        except Exception:
            pass

    try:
        if f := _read_pid_file():
            _kill_agent(f)
    except Exception as e:
        pkdlog("error={} stack={}", e, pkdexc())
    p = None
    try:
        pkjson.dump_pretty(p := PKDict(host=_get_host(), pid=os.getpid()), _PID_FILE)
        start()
    finally:
        _remove_own_pid_file(p)


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
        rv = _OpMsg(agentId=_cfg.agent_id, opName=op_name).pksetdefault(**kwargs)
        if not rv.get("opName"):
            raise AssertionError("missing opName in msg")
        return rv

    async def job_cmd_reply(self, msg, op_name, text=None, cmd=None, msg_items=None):
        def _fixup(reply):
            rv = PKDict(**msg_items) if msg_items else PKDict()
            if msg.opName in (job.OP_RUN, job.OP_RUN_STATUS):
                cmd.process_job_cmd_reply(reply)
                rv.pkupdate(
                    # Not a "reply", just a msg with all these values, no opId
                    msg=None,
                    op_name=job.OP_RUN_STATUS_UPDATE,
                    computeJid=msg.computeJid,
                    computeJobSerial=msg.computeJobSerial,
                    state=cmd.job_state,
                )
                if t := cmd.get("computeJobStart"):
                    rv.computeJobStart = t
                # Allow reply to override these things
                rv.pkupdate(reply)
            else:
                rv.pkupdate(msg=msg, reply=reply, op_name=op_name)
            return rv

        def _parse_text():
            if text is None:
                return PKDict()
            try:
                return pkjson.load_any(text)
            except Exception:
                return PKDict(
                    state=job.ERROR,
                    error="unable to parse job_cmd output",
                    stdout=text,
                    op_name=job.ERROR,
                )

        try:
            await self.send(self.format_op(**_fixup(_parse_text())))
        except Exception as e:
            pkdlog(
                "text={} msg_items={} error={} stack={}", text, msg_items, e, pkdexc()
            )
            # something is really wrong, because format_op is messed up
            raise

    async def loop(self):
        async def _connect_and_loop():
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
            rv = False
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
                # One success
                rv = True
            return rv

        t = _MAX_LOOP_RETRY
        while t > 0:
            self._websocket = None
            try:
                if await _connect_and_loop():
                    t = _MAX_LOOP_RETRY
            except Exception as e:
                if not isinstance(
                    e,
                    (
                        ConnectionError,
                        tornado.simple_httpclient.HTTPStreamClosedError,
                        tornado.iostream.StreamClosedError,
                    ),
                ):
                    pkdlog(
                        "retries countdown={}, websocket; error={} stack={}",
                        t,
                        e,
                        pkdexc(),
                    )
            finally:
                if self._websocket:
                    self._websocket.close()
            await tornado.gen.sleep(_LOOP_RETRY_SECS)
            t -= 1
        pkdlog("terminating after connection attempts={}", _MAX_LOOP_RETRY)
        self.terminate()

    def new_run_maybe_destroy_old(self, jid):
        for c in list(self.cmds):
            if c.jid == jid:
                c.destroy()

    async def send(self, msg):
        if not self._websocket:
            return False
        try:
            if not isinstance(msg, _OpMsg):
                raise AssertionError(f"expected _OpMsg not msg type={type(msg)}")
            await self._websocket.write_message(pkjson.dump_bytes(msg), binary=True)
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

    async def _cmd(self, msg, **kwargs):
        def _class(msg):
            if msg.jobRunMode == job.SBATCH:
                return _SbatchRun if msg.opName == job.OP_RUN else _SbatchCmd
            if msg.jobCmd == "fastcgi":
                return _FastCgiCmd
            return _Cmd

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
            c = _class(msg)(msg=msg, dispatcher=self, **kwargs)
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
        _call_later_0(self._fastcgi_loop, connection)

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
                            stack=stack,
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
            _assert_run_dir_exists(pkio.py_path(msg.runDir))
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
            if not self._fastcgi_msg_q:
                return self.format_op(
                    msg,
                    job.ERROR,
                    reply=PKDict(state=job.ERROR, error="fastcgi process got an error"),
                )
        if msg.jobCmd == "fastcgi":
            raise AssertionError("fastcgi called within fastcgi")
        self._fastcgi_msg_q.put_nowait(msg)
        # For better logging, msg.opId is used in format_op (reply)
        # Also used in op_cancel so a cancel, cancels the fastcgi process
        self.fastcgi_cmd.op_id = msg.opId
        return None

    async def _fastcgi_loop(self, connection):
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
                    text=await s.read_until(b"\n", job.cfg().max_message_bytes),
                )

        except Exception as e:
            if isinstance(e, tornado.iostream.StreamClosedError):
                pkdlog(
                    "msg={} stream closed unexpectedly exception={} real_error={}",
                    m,
                    e,
                    getattr(e, "real_error", None),
                )
            else:
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
        def _matches(op_id, jid):
            return list(c for c in self.cmds if c.op_id == op_id or c.jid == jid)

        for c in _matches(msg.get("opId", "no match"), msg.get("jid", "no match")):
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
        def _find():
            for c in list(self.cmds):
                if c.jid == msg.computeJid and c.get("job_state"):
                    return _reply(c)
            return None

        def _reply(cmd):
            if cmd.computeJobSerial != msg.computeJobSerial:
                pkdlog(
                    "expected computeJobSerial={} in msg={}", cmd.computeJobSerial, msg
                )
                # Supervisor is always right, so kill the job
                cmd.destroy()
                return self.format_op(
                    msg,
                    job.OP_ERROR,
                    reply=PKDict(
                        state=job.UNKNOWN, error="run_status computeJobSerial mismatch"
                    ),
                )

            return self.format_op(
                msg,
                job.OP_OK,
                reply=_copy_truthy(
                    cmd, PKDict(state=cmd.job_state), ("parallelStatus", "error")
                ),
            )

        if rv := _find():
            pass
        elif msg.jobRunMode == job.SBATCH:
            # Try to ask job_state for status of the job
            rv = _SbatchRunStatus.sbatch_status_request(msg=msg, dispatcher=self)
        else:
            # did not find job so assumed canceled, e.g. server restart
            rv = self.format_canceled(msg)
        pkdlog("reply={} computeJid={}", rv, msg.computeJid)
        return rv

    async def _op_sbatch_login(self, msg):
        return self.format_op(msg, job.OP_OK, reply=PKDict(loginSuccess=True))


class _Cmd(PKDict):
    def __init__(self, **kwargs):

        def _run():
            self.dispatcher.new_run_maybe_destroy_old(self.msg.computeJid)
            self.computeJobSerial = self.msg.computeJobSerial
            self.job_state = job.PENDING
            if self.msg.opName == job.OP_RUN:
                pkio.unchecked_remove(self.run_dir)
                pkio.mkdir_parent(self.run_dir)
                sirepo.sim_data.get_class(
                    self.msg.data.simulationType
                ).sim_run_input_to_run_dir(self.msg.data, self.run_dir)
            else:
                # Needs to exist for run_status so in_file can be created
                pkio.mkdir_parent(self.run_dir)

        super().__init__(**kwargs)
        self.pksetdefault(
            send_reply=True,
        ).pkupdate(
            _destroying=False,
            _terminating=False,
            _uid=job.split_jid(jid=self.msg.computeJid).uid,
            jid=self.msg.computeJid,
            op_id=self.msg.opId,
        )
        # only certain types of commands have runDir
        if self.msg.get("runDir"):
            self.run_dir = pkio.py_path(self.msg.runDir)
            if self.msg.opName in (job.OP_RUN, job.OP_RUN_STATUS):
                _run()
            else:
                _assert_run_dir_exists(self.run_dir)
        else:
            # POSIT: same as fast_cgi
            # Use agent's runDir.
            self.run_dir = pkio.py_path()
        self._process = _Process(self)
        self.dispatcher.cmds.append(self)

    def cancel_request(self):
        self.destroy()

    def destroy(self, terminating=False):
        if self._destroying:
            return
        if self.dispatcher.fastcgi_cmd == self:
            self.dispatcher.fastcgi_destroy()
        self._destroying = True
        self._terminating = terminating
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
            op_name=job.OP_OK,
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
            await self.dispatcher.job_cmd_reply(
                self.msg, job.OP_OK, text=text, cmd=self
            )
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

    def process_job_cmd_reply(self, reply):
        if "job_state" not in self:
            pkdlog("{} unexpected reply={}", self, reply)
            raise AssertionError("unexpected process_job_cmd_reply")
        _copy_truthy(reply, self, ("state", "parallelStatus", "error"))

    def start(self):
        try:
            self._in_file = self._create_in_file()
            self._process.start()
        except Exception as e:
            pkdlog("{} exception={} stack={}", self, e, pkdexc())
            rv = self.format_op(
                reply=PKDict(state=job.ERROR, error="failed to start process")
            )
            self.destroy()
            return rv

        _call_later_0(self._await_exit)
        if self.msg.opName != job.OP_RUN:
            return None
        self.job_state = job.RUNNING
        self.computeJobStart = int(time.time())
        rv = self.format_op_reply(state=job.STATE_OK)
        self.msg.opId = None
        self.msg.opName = job.OP_RUN_STATUS
        _call_later_0(
            self.dispatcher.job_cmd_reply,
            msg=self.msg,
            op_name=job.OP_RUN_STATUS_UPDATE,
            cmd=self,
        )
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
    pass


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
        pkdlog("{} returncode={}", self, returncode)
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
            if x := getattr(e, "real_error", None):
                raise AssertionError(f"real_error={x}")
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
        super().__init__(**kwargs)
        if "job_state" not in self:
            return
        self._sbatch_status_file = self.run_dir.join(_SBATCH_STATUS_FILE)
        self.msg.sbatchStatusFile = str(self._sbatch_status_file)
        # Only exists when _SbatchRun starts _SbatchRunStatus
        if r := self.pkdel("sbatch_run"):
            self._sbatch_status = r._sbatch_status.copy()
        else:
            self._sbatch_status = PKDict(
                job_cmd_state=None,
                sbatch_id=None,
                computeJobSerial=self.computeJobSerial,
                computeJobStart=None,
            )

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

    def _sbatch_status_update(self, want_write=True, **kwargs):
        def _cascade_to_self():
            if (
                s := self._sbatch_status.job_cmd_state
            ) != job.JOB_CMD_STATE_SBATCH_RUN_STATUS_STOP:
                self.job_state = s
            _copy_truthy(
                self._sbatch_status,
                self,
                ("computeJobStart", "parallelStatus", "error"),
            )

        p = self._sbatch_status.copy()
        self._sbatch_status.pkupdate(kwargs)
        if p == self._sbatch_status:
            return True
        _cascade_to_self()
        if not want_write:
            return True
        try:
            pkio.atomic_write(
                self._sbatch_status_file, pkjson.dump_pretty(self._sbatch_status)
            )
            return True
        except Exception as e:
            # The simulation directory might get deleted out from
            # under this process or some other error.
            pkdlog(
                "error writing file={} exception={} stack={}",
                self._sbatch_status_file,
                e,
                pkdexc(),
            )
            return False


class _SbatchRun(_SbatchCmd):

    def start(self):
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
            if self._sbatch_status_update(
                job_cmd_state=job.PENDING, sbatch_id=m.group(1)
            ):
                _SbatchRunStatus(
                    msg=copy.deepcopy(self.msg),
                    dispatcher=self.dispatcher,
                    sbatch_run=self,
                ).start()
                rv = self.format_op_reply(state=job.STATE_OK)
            else:
                rv = self.format_op(error="unable to write sbatch state file")
                # TODO(robnagler) need to cancel job, because no way to attach
        else:
            pkdlog("exit={} stdout={} stderr={}", p.returncode, p.stdout, p.stderr)
            rv = self.format_op(
                error=f"error submitting sbatch job error={p.stderr}",
            )
        self.destroy()
        return rv

    def _sbatch_script(self):
        def _nodes_tasks():
            if n := self.msg.get("sbatchNodes"):
                return f"#SBATCH --nodes={n}\n#SBATCH --cpus-per-task={self.msg.sbatchCores}"
            return f"#SBATCH --ntasks={self.msg.sbatchCores}"

        def _sim_run_dir_prepare():
            # python serialization does not work so use json
            return f"""{_python()} <<'EOF'
import sirepo.sim_data

sirepo.sim_data.get_class('{self.msg.data.simulationType}').sim_run_dir_prepare(
    '{self.run_dir}',
)
EOF"""

        def _python():
            return (
                "shifter --entrypoint " if self.msg.get("shifterImage") else ""
            ) + "python"

        def _shifter_header():
            # POSIT: job_api has validated values
            if not self.msg.get("shifterImage"):
                return ""
            return f"""#SBATCH --image={self.msg.shifterImage}
#SBATCH --constraint=cpu
#SBATCH --qos={self.msg.sbatchQueue}
#SBATCH --tasks-per-node={self.msg.tasksPerNode}
{sirepo.nersc.sbatch_project_option(self.msg.sbatchProject)}"""

        def _srun():
            return "srun" + (
                " --cpu-bind=cores" if self.msg.get("shifterImage") else ""
            )

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
{_sim_run_dir_prepare()}
# POSIT: same as return value of sim_run_dir_prepare
exec {_srun()} {_python()} {template_common.PARAMETERS_PYTHON_FILE}
"""
        )
        return f


class _SbatchRunStatus(_SbatchCmd):
    def __init__(self, **kwargs):
        kwargs["msg"].pkupdate(
            jobCmd="sbatch_parallel_status",
            opName=job.OP_RUN_STATUS,
        )
        super().__init__(**kwargs)
        self.pkdel("computeJobStart")
        self.pkupdate(
            _sbatch_status_cb=None,
            _sbatch_query_tries=0,
        )

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
        if self._sbatch_status_cb:
            self._sbatch_status_cb.stop()
            self._sbatch_status_cb = None
        if (
            self._sbatch_status.job_cmd_state not in job.JOB_CMD_STATE_EXITS
            and self._sbatch_status.sbatch_id
            and not terminating
        ):
            self._sbatch_status_update(job_cmd_state=job.CANCELED)
            _scancel(self._sbatch_status.sbatch_id)
        super().destroy(terminating=terminating)

    async def on_stdout_read(self, text):
        if self._destroying:
            return
        try:
            await self._sbatch_send_update(text=text)
        except Exception as e:
            pkdlog("{} text={} error={} stack={}", self, text, e, pkdexc())

    def process_job_cmd_reply(self, reply):
        super().process_job_cmd_reply(reply)
        if v := _copy_truthy(reply, PKDict(), ("parallelStatus", "error")):
            # job_cmd writes the final state so don't write again
            self._sbatch_status_update(
                want_write=reply.get("state") != job.COMPLETED, **v
            )

    @classmethod
    def sbatch_status_request(cls, **kwargs):
        self = cls(**kwargs)
        if s := self._sbatch_is_not_running():
            rv = self.format_op_reply(state=s)
            if x := self._sbatch_status.get("parallelStatus"):
                rv.parallelStatus = x
            self.destroy()
            return rv
        # can't answer the question yet
        rv = self.format_op_reply(state=job.UNKNOWN)
        # running, possibly completed, but needs to write parallel status
        self.start()
        return rv

    def start(self):
        # Detach from op_run_status or op_run
        self.op_id = self.msg.opId = None
        super().start()
        self._sbatch_status_cb = tornado.ioloop.PeriodicCallback(
            self._sbatch_poll_query,
            min(_MIN_SBATCH_POLL_SECS, self.msg.nextRequestSeconds) * 1000,
        )
        self._sbatch_status_cb.start()
        # So happens right away
        _call_later_0(self._sbatch_poll_query)
        return None

    def _sbatch_is_not_running(self):
        def _read():
            c = None
            try:
                c = self._sbatch_status_file.read()
                s = pkjson.load_any(c)
            except Exception as e:
                pkdlog(
                    "file={} exception={} contents={}", self._sbatch_status_file, e, c
                )
                return None
            if not s.get("sbatch_id") or not s.get("job_cmd_state"):
                pkdlog(
                    "invalid sbatch_status={} status={} file={}",
                    s,
                    self._sbatch_status_file,
                )
                return None
            if (x := self.msg.computeJobSerial) != s.get("computeJobSerial"):
                pkdlog(
                    "expected computeJobSerial={} status={} file={}",
                    x,
                    s,
                    self._sbatch_status_file,
                )
                return None
            return s

        if not self._sbatch_status_file.exists():
            # TODO(robnagler) could be missing run dir. Should cancel the job
            pkdlog("missing sbatch status file={}", self._sbatch_status_file)
            return job.CANCELED
        if not (s := _read()):
            if not pkconfig.in_dev_mode():
                pkio.unchecked_remove(self._sbatch_status_file)
            return job.CANCELED
        # save in self for start() and sbatch_status_request()
        self._sbatch_status_update(want_write=False, **s)
        if s.job_cmd_state in job.EXIT_STATUSES:
            return s.job_cmd_state
        return None

    async def _sbatch_poll_query(self):

        async def _sbatch_query_try_count_ok():
            if self._sbatch_query_tries < _MAX_SBATCH_QUERY_TRIES:
                return True
            pkdlog(
                "{} sbatch_query failed after tries={} sbatch_id={}",
                self,
                self._sbatch_query_tries,
                self._sbatch_status.sbatch_id,
            )
            self._sbatch_status_update(
                job_cmd_state=job.ERROR,
                error="sbatch_query unavailable or invalid output",
            )
            await self._sbatch_send_update()
            return False

        def _transition_state(prev, curr):
            if prev == curr or (
                curr == job.COMPLETED
                and prev == job.JOB_CMD_STATE_SBATCH_RUN_STATUS_STOP
            ):
                return False
            rv = True
            if prev == job.PENDING and curr in (job.RUNNING, job.COMPLETED):
                if not self._sbatch_status.get("computeJobStart"):
                    self._sbatch_status.computeJobStart = int(time.time())
            if curr == job.COMPLETED:
                curr = job.JOB_CMD_STATE_SBATCH_RUN_STATUS_STOP
                # waits for parallelStatus from job_cmd to send COMPLETED
                rv = False
            self._sbatch_status_update(job_cmd_state=curr)
            return rv

        try:
            if self._destroying:
                return
            self._sbatch_query_tries += 1
            if (
                not (s := self._sbatch_query())
                and not await _sbatch_query_try_count_ok()
            ):
                return
            self._sbatch_query_tries = 0
            if _transition_state(self._sbatch_status.job_cmd_state, s):
                await self._sbatch_send_update()
        except Exception as e:
            pkdlog("program error, stopping exception={} stack={}", e, pkdexc())
            try:
                await self.dispatcher.send(
                    self.dispatcher.format_op(
                        op_name=job.OP_RUN_STATUS_UPDATE,
                        msg=None,
                        computeJid=self.jid,
                        computeJobSerial=self.computeJobSerial,
                        error=f"_SbatchRunStatus exception={e}",
                        state=job.ERROR,
                    ),
                )
            except Exception as e:
                pkdlog("unable to send, stopping exception={} stack={}", e, pkdexc())
            self.destroy()

    def _sbatch_query(self):
        def _sacct():
            # Invalid job id specified (not running)
            p = subprocess.run(
                ("sacct", f"--jobs={self._sbatch_status.sbatch_id}", "--format=State"),
                cwd=str(self.run_dir),
                close_fds=True,
                capture_output=True,
                text=True,
            )
            if p.returncode != 0:
                pkdlog(
                    "{} sacct error exit={} sbatch={} stderr={} stdout={}",
                    self,
                    p.returncode,
                    self._sbatch_status.sbatch_id,
                    p.stderr,
                    p.stdout,
                )
                if "disabled" in p.stderr:
                    # Only in dev: saccount is not configured and job not running, assume canceled
                    return "CANCELLED"
                # Job never ran?
                return "FAILED"
            # sacct outputs state for each part of the job (shifter, external, etc.) so be pessimistic.
            rv = set()
            for l in re.split(r"\s+", p.stdout):
                if len(l) and not l.startswith("-") and l != "State":
                    rv.add(l)
            if len(rv) == 1:
                # Normal case
                return next(iter(rv))
            if len(rv) > 1 and "CANCELLED" in rv:
                return "CANCELLED"
            pkdlog("{} sacct parse failed words={} stdout={}", self, rv, p.stdout)
            return "FAILED"

        def _scontrol():
            # try scontrol first, because that's the normal case and easier to parse
            p = subprocess.run(
                ("scontrol", "show", "job", self._sbatch_status.sbatch_id),
                cwd=str(self.run_dir),
                close_fds=True,
                capture_output=True,
                text=True,
            )
            if p.returncode != 0:
                # Invalid job id will happen on NERSC. No jobs in dev
                if re.search("Invalid job id|No jobs", p.stderr):
                    pkdlog(
                        "sbatch={} not in system, trying sacct",
                        self._sbatch_status.sbatch_id,
                    )
                    return _sacct()
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

        if not (s := _scontrol()):
            return None
        if s in ("PENDING", "CONFIGURING"):
            return job.PENDING
        if s in ("COMPLETING", "RUNNING"):
            return job.RUNNING
        if s == "COMPLETED":
            return job.COMPLETED
        if s == "CANCELLED":
            return job.CANCELED
        if s == "FAILED":
            return job.ERROR
        if s == "TIMEOUT":
            return job.CANCELED
        pkdlog(
            "{} sbatch_id={} unexpected sbatch query state={}",
            self,
            self._sbatch_status.sbatch_id,
            s,
        )
        return job.ERROR

    async def _sbatch_send_update(self, text=None):
        def _optional():
            # parallelStatus only happens in the case we are at the end
            rv = PKDict()
            for f in "error", "parallelStatus", "computeJobStart":
                # Will be overwritten if in "text"
                if x := self._sbatch_status.get(f):
                    rv[f] = x
            return rv

        await self.dispatcher.job_cmd_reply(
            msg=self.msg,
            op_name=job.OP_RUN_STATUS_UPDATE,
            text=text,
            cmd=self,
            msg_items=_optional(),
        )
        if self._sbatch_status.job_cmd_state in job.EXIT_STATUSES:
            self.destroy()


def _assert_run_dir_exists(run_dir):
    if not run_dir.exists():
        raise _RunDirNotFound()


def _call_later_0(*args, **kwargs):
    return tornado.ioloop.IOLoop.current().call_later(0, *args, **kwargs)


def _copy_truthy(src, dst, keys):
    for x in keys:
        if y := src.get(x):
            dst[x] = y
    return dst


def _terminate(dispatcher):
    dispatcher.terminate()
