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

_SBATCH_ID_FILE = "sirepo_sbatch_id"

_SBATCH_STOPPED_FILE = "sbatch_status_stop"

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

    def format_op(self, msg, op_name, **kwargs):
        if msg:
            kwargs["opId"] = msg.get("opId")
        return pkjson.dump_bytes(
            PKDict(agentId=_cfg.agent_id, opName=op_name).pksetdefault(**kwargs),
        )

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
            await self.send(self.format_op(msg, op_name, reply=r))
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
            await self._websocket.write_message(msg)
            return True
        except Exception as e:
            pkdlog("msg={} error={}", msg, e)
            return False

    def terminate(self):
        try:
            x = self.cmds
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
            return _SbatchRun if msg.isParallel else _SbatchCmd
        elif msg.jobCmd == "fastcgi":
            return _FastCgiCmd
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
        self.terminate()
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
            if (
                msg.opName
                in (
                    job.OP_ANALYSIS,
                    job.OP_IO,
                )
                and msg.jobCmd != "fastcgi"
            ):
                return await self._fastcgi_op(msg)
            p = self._get_cmd_type(msg)(
                msg=msg, dispatcher=self, op_id=msg.opId, **kwargs
            )
        except _RunDirNotFound:
            return self.format_op(
                msg,
                job.OP_ERROR,
                reply=PKDict(runDirNotFound=True),
            )
        if msg.jobCmd == "fastcgi":
            self.fastcgi_cmd = p
        self.cmds.append(p)
        await p.start()
        return None

    def _fastcgi_accept(self, connection, *args, **kwargs):
        # Impedence mismatch: _fastcgi_accept cannot be async, because
        # bind_unix_socket doesn't await the callable.
        tornado.ioloop.IOLoop.current().add_callback(self._fastcgi_read, connection)

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
            _assert_run_dir_exists(pkio.py_path(msg.runDir))
        if not self.fastcgi_cmd:
            m = msg.copy()
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
                    job.OP_ANALYSIS,
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


class _Cmd(PKDict):
    def __init__(self, *args, send_reply=True, **kwargs):
        super().__init__(*args, send_reply=send_reply, **kwargs)
        if self.msg.opName not in job.SLOT_OPS:
            raise AssertionError(
                f"self.msg.opName={self.msg.opName} must be one of job.SLOT_OPS={job.SLOT_OPS} to create _Cmd"
            )
        self.run_dir = pkio.py_path(self.msg.runDir)
        self._is_compute = self.msg.jobCmd == "compute"
        if self._is_compute:
            pkio.unchecked_remove(self.run_dir)
            pkio.mkdir_parent(self.run_dir)
        self._in_file = self._create_in_file()
        self._process = _Process(self)
        self._destroying = False
        self._terminating = False
        self._start_time = int(time.time())
        self.jid = self.msg.computeJid
        self._uid = job.split_jid(jid=self.jid).uid

    def destroy(self, terminating=False):
        self._destroying = True
        self._terminating = terminating
        if "_in_file" in self:
            pkio.unchecked_remove(self.pkdel("_in_file"))
        self._process.kill()
        try:
            self.dispatcher.cmds.remove(self)
        except ValueError:
            pass

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
                self.dispatcher.format_op(
                    self.msg,
                    job.OP_JOB_CMD_STDERR,
                    stderr=text.decode("utf-8", errors="ignore"),
                )
            )
        except Exception as exc:
            pkdlog("{} text={} error={} stack={}", self, text, exc, pkdexc())

    async def on_stdout_read(self, text):
        if self._destroying or not self.send_reply:
            return
        await self._job_cmd_reply(text)

    async def start(self):
        if self._is_compute and self._start_time:
            await self.dispatcher.send(
                self.dispatcher.format_op(
                    self.msg,
                    job.OP_RUN,
                    reply=PKDict(state=job.RUNNING, computeJobStart=self._start_time),
                ),
            )
        self._process.start()
        tornado.ioloop.IOLoop.current().add_callback(self._await_exit)

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
                    self.dispatcher.format_op(
                        self.msg,
                        job.OP_ERROR,
                        error=e,
                        reply=PKDict(
                            state=job.ERROR,
                            error=f"process exit={self._process.returncode} jid={self.jid}",
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
                self.dispatcher.format_op(
                    self.msg,
                    job.OP_ERROR,
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

    async def _job_cmd_reply(self, text):
        try:
            await self.dispatcher.job_cmd_reply(
                self.msg,
                job.OP_RUN if self._is_compute else job.OP_ANALYSIS,
                text,
            )
        except Exception as e:
            pkdlog("{} text={} error={} stack={}", self, text, e, pkdexc())


class _FastCgiCmd(_Cmd):
    def destroy(self, terminating=False):
        self.dispatcher.fastcgi_destroy()
        super().destroy(terminating=terminating)


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
            e.PYTHONPATH = _DEV_PYTHON_PATH
        return super().job_cmd_env(e)


class _SbatchPrepareSimulationCmd(_SbatchCmd):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, send_reply=False, **kwargs)

    async def _await_exit(self):
        await self._process.exit_ready()
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

    async def on_stderr_read(self, text):
        pkdlog("self={} stderr={}", self, text)

    async def on_stdout_read(self, text):
        self.stdout = text
        pkdlog("self={} stdout={}", self, self.stdout)


class _SbatchRun(_SbatchCmd):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pkupdate(
            _sbatch_id=None,
            _sbatch_id_file=self.run_dir.join(_SBATCH_ID_FILE),
            _start_time=0,
            _status="PENDING",
            _status_cb=None,
            _stopped_sentinel=self.run_dir.join(_SBATCH_STOPPED_FILE),
        )
        self.msg.jobCmd = "sbatch_status"
        # pkdel so does not get removed twice (see destroy)
        self.pkdel("_in_file").remove()

    async def _await_start_ready(self):
        await self._start_ready.wait()
        if self._destroying:
            return
        # in_file now contains sbatch_id
        self._in_file = self._create_in_file()
        pkdlog(
            "{} sbatch_id={} starting jobCmd={}",
            self,
            self._sbatch_id,
            self.msg.jobCmd,
        )
        await super().start()

    def destroy(self, terminating=False):
        self._destroying = True
        self._terminating = terminating
        if self._status_cb:
            self._status_cb.stop()
            self._status_cb = None
        self._start_ready.set()
        if self._sbatch_id and not self._terminating:
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
        super().destroy(terminating=terminating)

    async def start(self):
        await self._prepare_simulation()
        if self._destroying:
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
            await self.dispatcher.send(
                self.dispatcher.format_op(
                    self.msg,
                    job.OP_ERROR,
                    error=f"error submitting sbatch job error={p.stderr}",
                    reply=PKDict(
                        state=job.ERROR,
                        error=p.stderr,
                    ),
                )
            )
            raise ValueError(
                f"Unable to submit exit={p.returncode} stdout={p.stdout} stderr={p.stderr}"
            )
        self._sbatch_id = m.group(1)
        self._sbatch_id_file.write(self._sbatch_id)
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

    async def _prepare_simulation(self):
        c = _SbatchPrepareSimulationCmd(
            dispatcher=self.dispatcher,
            msg=self.msg.copy().pkupdate(
                jobCmd="prepare_simulation",
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
        if self._destroying:
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
            self._destroying = True
            pkdlog(
                "{} sbatch_id={} unexpected state={}",
                self,
                self._sbatch_id,
                self._status,
            )
            await self.dispatcher.send(
                self.dispatcher.format_op(
                    self.msg,
                    job.OP_ERROR,
                    reply=PKDict(
                        state=job.ERROR, error=f"sbatch status={self._status}"
                    ),
                )
            )
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
        if self.cmd.msg.jobCmd not in ("prepare_simulation", "compute"):
            _assert_run_dir_exists(self.cmd.run_dir)

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
    dispatcher.terminate()
    # just in case isn't removed by start_sbatch
    pkio.unchecked_remove(_PID_FILE)
