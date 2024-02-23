"""Agent for managing the execution of jobs.

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern import pkcompat
from pykern import pkconfig
from pykern import pkio
from pykern import pkjson
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdlog, pkdp, pkdexc, pkdc, pkdformat
from sirepo import job
from sirepo.template import template_common
import asyncio
import datetime
import json
import os
import re
import shutil
import signal
import sirepo.feature_config
import sirepo.modules
import sirepo.nersc
import sirepo.quest
import sirepo.tornado
import socket
import subprocess
import sys
import time
import tornado.gen
import tornado.ioloop
import tornado.iostream
import tornado.locks
import tornado.process
import tornado.websocket
import tornado.netutil


#: How often to poll in loop()
_RETRY_SECS = 1

#: Reasonable over the Internet connection
_CONNECT_SECS = 10

_FASTCGI_RESTART_SECS = 10

_IN_FILE = "in-{}.json"

_PID_FILE = "job_agent.pid"

_cfg = None

_NEWLINE = b"\n"[0]


def start():
    # TODO(robnagler) commands need their own init hook like the server has
    global _cfg

    _cfg = pkconfig.init(
        agent_id=pkconfig.Required(str, "id of this agent"),
        # POSIT: same as job_driver.DriverBase._agent_env
        dev_source_dirs=(
            pkconfig.in_dev_mode(),
            bool,
            "add ~/src/radiasoft/{pykern,sirepo} to $PYTHONPATH",
        ),
        fastcgi_sock_dir=(
            pkio.py_path("/tmp"),
            pkio.py_path,
            "directory of fastcfgi socket, must be less than 50 chars",
        ),
        global_resources_server_token=pkconfig.Required(
            str,
            "credential for global resources server",
        ),
        global_resources_server_uri=pkconfig.Required(
            str,
            "how to connect to global resources",
        ),
        run_mode=pkconfig.Required(str, "one of sirepo.job.RUN_MODES"),
        sim_db_file_server_token=pkconfig.Required(
            str,
            "credential for sim db files",
        ),
        sim_db_file_server_uri=pkconfig.Required(
            str,
            "how to connect to sim db files",
        ),
        start_delay=(0, pkconfig.parse_seconds, "delay startup in internal_test mode"),
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


class _Dispatcher(PKDict):
    def __init__(self):
        super().__init__(
            _is_destroyed=False,
            cmds=[],
            fastcgi_proxies=PKDict(),
        )
        for o in job.SLOT_OPS:
            # Only start sequential ops (not sbatch or parallel)
            if o != job.OP_RUN or _cfg.run_mode == job.RUN_MODE_SEQUENTIAL:
                self.fastcgi_proxies[o] = _FastCgiProxy(op_name=o, dispatcher=self)
        with sirepo.quest.start() as qcall:
            self.uid = qcall.auth.logged_in_user(check_path=False)

    def destroy(self):
        if self._is_destroyed:
            return
        self._is_destroyed = True
        try:
            x = self.cmds
            self.cmds = []
            for c in x:
                try:
                    c.destroy()
                except Exception as e:
                    pkdlog("cmd={} error={} stack={}", c, e, pkdexc())
            return None
        finally:
            tornado.ioloop.IOLoop.current().stop()

    def format_op(self, msg, op_name, **kwargs):
        if msg:
            kwargs["opId"] = msg.get("opId")
        return pkjson.dump_bytes(
            PKDict(agentId=_cfg.agent_id, opName=op_name).pksetdefault(**kwargs),
        )

    async def job_cmd_reply(self, msg, op_name, text):
        try:
            # implicitly checks that the message is the right size,
            # because the last thing before the newline should be a
            # closing brace and that will be truncated with read_until.
            r = pkjson.load_any(text)
        except Exception as e:
            await self.send_error(
                msg,
                f"pkjson.load_any exception={e} len(text)={len(text)}",
                "unable to parse job_cmd output",
            )
            return
        try:
            await self.send(self.format_op(msg, op_name, reply=r))
        except Exception as e:
            pkdlog("msg={} reply={} error={} stack={}", msg, r, e, pkdexc())
            # something is really wrong, because format_op or send is messed up
            raise

    async def loop(self):
        while True:
            self._websocket = None
            try:
                self._websocket = await tornado.websocket.websocket_connect(
                    tornado.httpclient.HTTPRequest(
                        connect_timeout=_CONNECT_SECS,
                        url=_cfg.supervisor_uri,
                        validate_cert=sirepo.job.cfg().verify_tls,
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
                            "websocket closed for reply=None to len(send)={} send={}",
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
            await self._websocket.write_message(msg)
            return True
        except Exception as e:
            pkdlog("msg={} error={}", msg, e)
            return False

    async def send_error(msg, error, user_alert):
        try:
            await self.send(
                self.format_op(
                    msg,
                    job.OP_ERROR,
                    error=error,
                    reply=PKDict(
                        state=job.ERROR,
                        error=user_alert,
                    ),
                )
            )
        except Exception as e:
            pkdlog(
                "msg={} original_error={} exception={} stack={}",
                msg,
                error,
                e,
                pkdexc(),
            )

    def _get_cmd_type(self, msg):
        if msg.jobRunMode == job.RUN_MODE_SBATCH:
            return _SbatchRun if msg.isParallel else _SbatchCmd
        return _Cmd

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

    async def _op_cancel(self, msg):
        await self.send(
            self.format_op(msg, job.OP_OK, reply=PKDict(state=job.CANCELED)),
        )
        for c in list(self.cmds):
            if c.op_id in msg.opIdsToCancel:
                pkdlog("cmd={}", c)
                c.destroy()
        return None

    async def _op_io(self, msg):
        return await self._cmd(msg)

    async def _op_kill(self, msg):
        self.destroy()
        return None

    async def _op_run(self, msg):
        return await self._cmd(msg)

    async def _op_sbatch_login(self, msg):
        await self.send(
            self.format_op(msg, job.OP_OK, reply=PKDict(loginSuccess=True)),
        )

    async def _op_begin_session(self, msg):
        await self.send(
            self.format_op(msg, job.OP_OK, reply=PKDict(awake=True)),
        )
        return None

    async def _cmd(self, msg, **kwargs):
        try:
            if c := self.fastcgi_proxies.get(msg.opName):
                return c.send_cmd(msg)
            p = self._get_cmd_type(msg)(
                msg=msg, dispatcher=self, op_id=msg.opId, **kwargs
            )
        except _RunDirNotFound:
            return self.format_op(
                msg,
                job.OP_ERROR,
                reply=PKDict(state=job.ERROR, runDirNotFound=True),
            )
        self.cmds.append(p)
        await p.start()
        return None


class _Cmd(PKDict):
    def __init__(self, send_reply=True, **kwargs):
        super().__init__(send_reply=send_reply, _is_destroyed=False, **kwargs)
        self._maybe_start_compute_run()
        self._in_file = self._create_in_file()
        self._process = _Process(self)
        self._terminating = False
        self.jid = self.msg.get("computeJid", None)

    def destroy(self):
        if self._is_destroyed:
            return
        self._is_destroyed = True
        self._process.kill()
        self._subclass_destroy()
        if "_in_file" in self:
            pkio.unchecked_remove(self.pkdel("_in_file"))
        if self in self.dispatcher.cmds:
            self.dispatcher.cmds.remove(self)

    def job_cmd_cmd(self):
        return ("sirepo", "job_cmd", self._in_file)

    def job_cmd_cmd_stdin_env(self):
        return job.agent_cmd_stdin_env(
            cmd=self.job_cmd_cmd(),
            env=self.job_cmd_env(),
            source_bashrc=self.job_cmd_source_bashrc(),
            uid=self.dispatcher.uid,
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
            uid=self.dispatcher.uid,
        )

    def job_cmd_source_bashrc(self):
        if sirepo.feature_config.cfg().trust_sh_env:
            return ""
        return "source $HOME/.bashrc"

    async def on_stderr_read(self, text):
        if self._is_destroyed:
            return
        try:
            await self.dispatcher.send(
                self.dispatcher.format_op(
                    self.msg,
                    job.OP_JOB_CMD_STDERR,
                    stderr=text.decode("utf-8", errors="ignore"),
                )
            )
        except Exception as exc:
            pkdlog("{} text={} error={} stack={}", self, text, exc, pkdexc())

    async def on_stdout_read(self, text):
        if self._is_destroyed or not self.send_reply:
            return
        try:
            await self.dispatcher.job_cmd_reply(
                self.msg,
                job.OP_RUN if self._is_compute else job.OP_ANALYSIS,
                text,
            )
        except Exception as e:
            pkdlog("{} text={} error={} stack={}", self, text, e, pkdexc())

    def pkdebug_str(self):
        return pkdformat(
            "{}(a={:.4} jid={} o={:.4} job_cmd={} run_dir={})",
            self.__class__.__name__,
            _cfg.agent_id,
            self.jid,
            self.op_id,
            self.msg.jobCmd,
            self.run_dir,
        )

    async def start(self):
        await self._maybe_reply_running()
        if self._is_destroyed:
            return
        self._process.start()
        tornado.ioloop.IOLoop.current().add_callback(self._await_exit)

    async def _await_exit(self):
        try:
            await self._process.exit_ready()
            e = self._process.stderr.text.decode("utf-8", errors="ignore")
            if e or self._process.returncode != 0:
                pkdlog("{} exit={} stderr={}", self, self._process.returncode, e)
            if self._is_destroyed:
                return
            if self._process.returncode != 0:
                x = f"process exit={self._process.returncode}"
                await self.dispatcher.send_error(
                    self.msg,
                    f"{x} jid={self.jid} stderr={e}",
                    x,
                )
        except Exception as exc:
            if self._is_destroyed:
                return
            pkdlog(
                "{} error={} returncode={} stack={}",
                self,
                exc,
                self._process.returncode,
                pkdexc(),
            )
            await self.dispatcher.send_error(self.msg, str(exc), "job_agent error")
        finally:
            self.destroy()

    def _create_in_file(self):
        f = self.run_dir.join(
            _IN_FILE.format(job.unique_key()),
        )
        pkjson.dump_pretty(self.msg, filename=f, pretty=False)
        return f

    async def _maybe_reply_running(self):
        if not self._is_compute or not self._start_time:
            return
        await self.dispatcher.send(
            self.dispatcher.format_op(
                self.msg,
                job.OP_RUN,
                reply=PKDict(state=job.RUNNING, computeJobStart=self._start_time),
            ),
        )

    def _maybe_start_compute_run(self):
        self.run_dir = pkio.py_path(self.msg.runDir)
        self._is_compute = self.msg.jobCmd == job.CMD_COMPUTE_RUN
        if self._is_compute:
            pkio.unchecked_remove(self.run_dir)
            pkio.mkdir_parent(self.run_dir)
            self._start_time = int(time.time())
        else:
            if not self.run_dir.exists():
                raise _RunDirNotFound()
            self._start_time = 0

    def _subclass_destroy(self):
        pass


class _FastCgiProcess(_Cmd):
    """Starts a single _Cmd which processes msgs instead of a _Cmd per msg."""

    def __init__(self, op_name, **kwargs):
        """Start the fastcgi process

        Args:
            op_name (str): which slot
            dispatcher (_Dispatcher): back link
        Returns:
            self: instance
        """
        m = PKDict()
        m.jobCmd = job.CMD_FASTCGI
        # Runs in an agent's directory and chdirs to real runDirs.
        # Except in stateless_compute which doesn't interact with the db.
        m.runDir = pkio.py_path()
        s = _cfg.fastcgi_sock_dir.join(
            f"sirepo_job_cmd-{_cfg.agent_id:8}-{op_name}.sock",
        )
        pkio.unchecked_remove(s)
        m.socket = str(s)
        super().__init__(
            msg=m,
            op_name=op_name,
            op_id=None,
            send_reply=False,
            **kwargs,
        )
        self._socket = s
        self._msg_q = sirepo.tornado.Queue(1)
        # Listen first so job_cmd can connect
        self._remove_accept_handler = tornado.netutil.add_accept_handler(
            tornado.netutil.bind_unix_socket(str(self._socket)),
            self._accept,
        )

    async def on_stdout_read(self, text):
        if self._is_destroyed:
            return
        await self.on_stderr_read(
            pkcompat.to_bytes(f"unexpected output from fastcgi msg={self.msg} stdout=")
            + text,
        )

    def pkdebug_str(self):
        return pkdformat(
            "{}(a={:.4} uid={} op_name={})",
            self.__class__.__name__,
            _cfg.agent_id,
            self.op_name,
            self.dispatcher.uid,
        )

    def send_cmd(self, msg):
        self._msg_q.put_nowait(msg)
        return None

    def _accept(self, connection, *args, **kwargs):
        tornado.ioloop.IOLoop.current().add_callback(self._read, connection)

    async def _await_exit(self):
        try:
            await self._process.exit_ready()
            e = self._process.stderr.text.decode("utf-8", errors="ignore")
            if e or self._process.returncode != 0:
                pkdlog("{} exit={} stderr={}", self, self._process.returncode, e)
        except Exception as e:
            pkdlog("{} exception={}", self, e)
        finally:
            await self._handle_exit()

    async def _read(self, connection):
        s = None
        m = None
        err = None
        try:
            s = tornado.iostream.IOStream(
                connection,
                max_buffer_size=job.cfg().max_message_bytes,
            )
            while True:
                self.msg = m = await self._msg_q.get()
                if self._is_destroyed:
                    return
                # Avoid issues with exceptions. We don't use q.join()
                # so not an issue to call before work is done.
                self._msg_q.task_done()
                # Updates run_dir, _start_time, _is_compute on self
                self._maybe_start_compute_run()
                await self._maybe_reply_running()
                if self._is_destroyed:
                    return
                await s.write(pkjson.dump_bytes(m) + b"\n")
                if self._is_destroyed:
                    return
                r = await s.read_until(b"\n", job.cfg().max_message_bytes)
                if r is not None:
                    # This will reply always, even if the message is corrupt (error)
                    await self.dispatcher.job_cmd_reply(m, self.op_name, r)
                if self._is_destroyed:
                    return
                self.msg = m = None
                if r[-1] != _NEWLINE:
                    raise AssertionError(
                        pkdformat("truncated reply read from socket self={}", self),
                    )
        except Exception as e:
            pkdlog("msg={} error={} stack={}", m, e, pkdexc())
            if self._is_destroyed:
                return
            if m:
                self.msg_q.put_nowait(m)
        finally:
            if s:
                s.close()
            # some type of error that's not a terminate so restart
            await self._handle_exit()

    def _subclass_destroy(self):
        self.proxy.destroy_process(self)
        # if _read is waiting, this will release it.
        # May not matter, but is complete
        if self._msg_q:
            self._msg_q.put_nowait(PKDict())
            self._msg_q = None
        if self._remove_accept_handler:
            self._remove_accept_handler()
            self._remove_accept_handler = None
        if self._socket:
            pkio.unchecked_remove(self._socket)
            self._socket = None

    async def _handle_exit(self):
        """Destroy and possibly create a new instance"""
        if self._is_destroyed:
            return
        # destroy _fastcgi state first (synchronously), then maybe
        # send errors to avoid asynchronous modification
        d = self.dispatcher
        q = self._msg_q
        self._msg_q = None
        self.destroy()
        while q.qsize() > 0:
            await d.send_error(
                q.get_nowait(), "unexpected fastcgi exit", "internal error"
            )
            q.task_done()


class _FastCgiProxy(PKDict):
    """Manages a single _FastCgiProcess"""

    def __init__(self, **kwargs):
        """Creates proxy and does not start process

        Args:
            op_name (str): which slot
            dispatcher (_Dispatcher): back link
        Returns:
            self: instance
        """
        super().__init__(
            _running=sirepo.tornado.Event(),
            _process=None,
            _starts=[],
            **kwargs,
        )

    def destroy_process(self, process):
        # command destroys itself
        self._process = None

    def send_cmd(self, msg):
        if self._process is not None:
            self._process = _FastCgiProcess.create(
                op_name=self.op_name, dispatcher=self.dispatcher
            )
            asyncio.create_task(self._start())
        # Synchronous so messages are always queued in the proper order
        self._process.send_cmd(msg)

    async def _start(self):
        if self._starts and self._starts[-1] + _FASTCGI_RESTART_SECS > int(time.time()):
            # Restarts should be fine. If not, at least we wait a bit before recreating.
            await asyncio.sleep(_FASTCGI_RESTART_SECS)
            if self._process.is_destroyed:
                # This should not happen, but correct way to code this
                return
        # TODO(robnagler) limit restarts by killing agent(?)
        self._starts.append(int(time.time()))
        pkdlog(
            "_FastCgiProcess op_name={} starts[-3:]={}", self.op_name, self._starts[-3:]
        )
        await self._process.start()


class _SbatchCmd(_Cmd):
    async def exited(self):
        await self._process.exit_ready()

    def job_cmd_source_bashrc(self):
        if not self.msg.get("shifterImage"):
            return super().job_cmd_source_bashrc()
        return ""

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
            h = pkio.py_path("~/src/radiasoft")
            e.PYTHONPATH = "{}:{}".format(h.join("sirepo"), h.join("pykern"))
        return super().job_cmd_env(e)


class _SbatchPrepareSimulationCmd(_SbatchCmd):
    def __init__(self, **kwargs):
        super().__init__(send_reply=False, **kwargs)

    async def _await_exit(self):
        await self._process.exit_ready()
        if self._is_destroyed:
            return
        s = job.ERROR
        o = None
        if "stdout" in self:
            o = pkjson.load_any(self.stdout)
            s = o.get("state")
        if s != job.COMPLETED:
            raise AssertionError(
                pkdformat(
                    "unexpected state={} from result of cmd={} stdout={}",
                    s,
                    self,
                    o,
                )
            )

    async def on_stdout_read(self, text):
        self.stdout = text
        pkdlog("self={} stdout={}", self, self.stdout)


class _SbatchRun(_SbatchCmd):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.pkupdate(
            _start_time=0,
            _sbatch_id=None,
            _status_cb=None,
            _status="PENDING",
            _stopped_sentinel=self.run_dir.join("sbatch_status_stop"),
        )
        self.msg.jobCmd = job.CMD_SBATCH_STATUS
        self.pkdel("_in_file").remove()

    async def _await_start_ready(self):
        await self._start_ready.wait()
        if self._is_destroyed:
            return
        self._in_file = self._create_in_file()
        pkdlog(
            "{} sbatch_id={} starting jobCmd={}",
            self,
            self._sbatch_id,
            self.msg.jobCmd,
        )
        await super().start()

    async def start(self):
        await self._prepare_simulation()
        if self._terminating:
            return
        p = subprocess.run(
            ("sbatch", self._sbatch_script()),
            close_fds=True,
            cwd=str(self.run_dir),
            capture_output=True,
            text=True,
        )
        m = re.search(r"Submitted batch job (\d+)", p.stdout)
        # TODO(robnagler) if the guy is out of hours, will fail
        if not m:
            await self.dispatcher.send_error(
                self.msg,
                f"error submitting sbatch job error={p.stderr}",
                p.stderr,
            )
            raise ValueError(
                f"Unable to submit exit={p.returncode} stdout={p.stdout} stderr={p.stderr}"
            )
        self._sbatch_id = m.group(1)
        self.msg.pkupdate(
            sbatchId=self._sbatch_id,
            stopSentinel=str(self._stopped_sentinel),
        )
        self._status_cb = tornado.ioloop.PeriodicCallback(
            self._sbatch_status,
            self.msg.nextRequestSeconds * 1000,
        )
        self._start_ready = sirepo.tornado.Event()
        self._status_cb.start()
        # Starting an sbatch job may involve a long wait in the queue
        # so release back to agent loop so we can process other ops
        # while we wait for the job to start running
        tornado.ioloop.IOLoop.current().add_callback(self._await_start_ready)

    def _subclass_destroy(self):
        if self._status_cb:
            self._status_cb.stop()
            self._status_cb = None
        self._start_ready.set()
        if self._sbatch_id:
            i = self._sbatch_id
            self._sbatch_id = None
            p = subprocess.run(
                ("scancel", "--full", "--quiet", i),
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
                    i,
                    p.stderr,
                    p.stdout,
                )

    async def _prepare_simulation(self):
        c = _SbatchPrepareSimulationCmd(
            dispatcher=self.dispatcher,
            msg=self.msg.copy().pkupdate(
                jobCmd=job.CMD_PREPARE_SIMULATION,
                # sequential job
                opName=job.OP_ANALYSIS,
            ),
            op_id=self.msg.opId,
        )
        await c.start()
        await c._await_exit()

    def _sbatch_script(self):
        i = self.msg.shifterImage
        s = o = ""
        # POSIT: job_api has validated values
        if i:
            o = f"""#SBATCH --image={i}
#SBATCH --constraint=cpu
#SBATCH --qos={self.msg.sbatchQueue}
#SBATCH --tasks-per-node={self.msg.tasksPerNode}
{sirepo.nersc.sbatch_project_option(self.msg.sbatchProject)}"""
            s = "--cpu-bind=cores shifter --entrypoint"
        f = self.run_dir.join(self.jid + ".sbatch")
        if "sbatchNodes" in self.msg:
            n = f"""#SBATCH --nodes={self.msg.sbatchNodes}
#SBATCH --cpus-per-task={self.msg.sbatchCores}"""
        else:
            n = f"#SBATCH --ntasks={self.msg.sbatchCores}"
        f.write(
            f"""#!/bin/bash
#SBATCH --error={template_common.RUN_LOG}
{n}
#SBATCH --output={template_common.RUN_LOG}
#SBATCH --time={self._sbatch_time()}
{o}
{self.job_cmd_env()}
{self.job_cmd_source_bashrc()}
exec srun {s} python {template_common.PARAMETERS_PYTHON_FILE}
"""
        )
        return f

    async def _sbatch_status(self):
        if self._terminating:
            return
        p = subprocess.run(
            ("scontrol", "show", "job", self.msg.sbatchId),
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
                self._sbatch_id,
                p.stderr,
                p.stdout,
            )
            return
        r = re.search(r"(?<=JobState=)(\S+)(?= Reason)", p.stdout)
        if not r:
            pkdlog(
                "{} failed to find JobState in sderr={} stdout={}",
                self,
                p.stderr,
                p.stdout,
            )
            return
        self._status = r.group()
        if self._status in ("PENDING", "CONFIGURING"):
            return
        else:
            if not self._start_ready.is_set():
                self._start_time = int(time.time())
                self._start_ready.set()
            if self._status in ("COMPLETING", "RUNNING"):
                return
        c = self._status == "COMPLETED"
        self._stopped_sentinel.write(job.COMPLETED if c else job.ERROR)
        if not c:
            # because have to await before calling destroy
            self._terminating = True
            pkdlog(
                "{} sbatch_id={} unexpected state={}",
                self,
                self._sbatch_id,
                self._status,
            )
            e = (f"sbatch status={self._status}",)
            await self.dispatcher.send_error(self.msg, e, e)
            self.destroy()

    def _sbatch_time(self):
        return str(
            datetime.timedelta(
                seconds=int(
                    datetime.timedelta(
                        hours=float(self.msg.sbatchHours)
                    ).total_seconds(),
                ),
            )
        )


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
        # TODO(e-carlin): Terminate?
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
        tornado.ioloop.IOLoop.current().add_callback(self._begin_read_stream)

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


def _terminate(dispatcher):
    dispatcher.destroy()
    pkio.unchecked_remove(_PID_FILE)
