# -*- coding: utf-8 -*-
"""Agent for managing the execution of jobs.

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkcollections
from pykern import pkconfig
from pykern import pkio
from pykern import pkjson
from pykern.pkcollections import PKDict
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdlog, pkdp, pkdexc, pkdc
from sirepo import job_agent_process, job, mpi, simulation_db
from sirepo.pkcli import job_process
import json
import os
import re
import signal
import subprocess
import sys
import time
import tornado.gen
import tornado.httpclient
import tornado.ioloop
import tornado.locks
import tornado.process
import tornado.queues
import tornado.websocket

#: Long enough for job_process to write result in run_dir
_TERMINATE_SECS = 3

_RETRY_SECS = 1

_IN_FILE = 'in-{}.json'

_INFO_FILE = 'job-agent.json'

_INFO_FILE_COMMON = PKDict(version=1)

#: Need to remove $OMPI and $PMIX to prevent PMIX ERROR:
# See https://github.com/radiasoft/sirepo/issues/1323
# We also remove SIREPO_ and PYKERN vars, because we shouldn't
# need to pass any of that on, just like runner.docker, doesn't
_EXEC_ENV_REMOVE = re.compile('^(OMPI_|PMIX_|SIREPO_|PYKERN_)')

cfg = None


def default_command():
    os.environ['PYKERN_PKDEBUG_OUTPUT'] = '/dev/tty'
    os.environ['PYKERN_PKDEBUG_REDIRECT_LOGGING'] = '1'
    os.environ['PYKERN_PKDEBUG_CONTROL'] = '.*'

    job.init()
    global cfg

    cfg = pkconfig.init(
        agent_id=pkconfig.Required(str, 'id of this agent'),
        supervisor_uri=pkconfig.Required(
            str, 'how to connect to the supervisor'),
    )
    pkdlog('{}', cfg)
    i = tornado.ioloop.IOLoop.current()
    c = _Comm()
    def s(n, x): return i.add_callback_from_signal(c.kill)
    signal.signal(signal.SIGTERM, s)
    signal.signal(signal.SIGINT, s)
    i.spawn_callback(c.loop)
    i.start()


class _JobProcess(PKDict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._subprocess = None
        self._in_file = None
        self._parsed_stdout = None
        self._parsed_stderr = None
        self._raw_stdout = bytearray()
        self._raw_stderr = bytearray()
        self._subprocess_exit_event = tornado.locks.Event()
        self._stdout_read_done = tornado.locks.Event()
        self._stderr_read_done = tornado.locks.Event()

    async def exit(self):
        await self._subprocess_exit_event.wait()
        return self._parsed_stdout, self._parsed_stderr

    def kill(self):
        # TODO(e-carlin): Terminate?
        self._subprocess.proc.kill()

    def start(self):
        # SECURITY: msg must not contain agentId
        assert not self.msg.get('agentId')
        env = self._subprocess_env()
        self._in_file = self.msg.runDir.join(
            _IN_FILE.format(job.unique_key()))
        # pkio.mkdir_parent_only(self._in_file) # TODO(e-carlin): Hack for animations. Who should be ensuring this?
        # TODO(e-carlin): Find a better solution for serial and deserialization
        self.msg.runDir = str(self.msg.runDir)
        pkjson.dump_pretty(self.msg, filename=self._in_file, pretty=False)
        self._subprocess = tornado.process.Subprocess(
            ('pyenv', 'exec', 'sirepo', 'job_process', str(self._in_file)),
            # SECURITY: need to change cwd, because agentDir has agentId
            cwd=self.msg.runDir,
            start_new_session=True,
            stdin=subprocess.DEVNULL,
            stdout=tornado.process.Subprocess.STREAM,
            stderr=tornado.process.Subprocess.STREAM,
            env=env,
        )

        async def collect(stream, out, event):
            out.extend(await stream.read_until_close())
            event.set()
        i = tornado.ioloop.IOLoop.current()
        i.add_callback(collect, self._subprocess.stdout,
                       self._raw_stdout, self._stdout_read_done)
        i.add_callback(collect, self._subprocess.stderr,
                       self._raw_stderr, self._stderr_read_done)
        self._subprocess.set_exit_callback(self._subprocess_exit)

    async def _load_output(self):
        o = None
        e = None
        # TODO(e-carlin): If we can increase the pipe buffer size then we don't
        # have to spawn_callback's for collect() and could just read the output
        # of the job process here.
        await self._stdout_read_done.wait()
        await self._stderr_read_done.wait()
        try:
            e = pkjson.load_any(self._raw_stderr)
        except json.JSONDecodeError:
            e = self._raw_stderr.decode('utf-8')
        except Exception as e:
            pass
        if e:
            try:
                o = pkjson.load_any(self._raw_stdout)
            except json.JSONDecodeError:
                pass
            if isinstance(e, PKDict):
                if 'error_log' in e:
                    e = e.error_log
                elif 'error' in e:
                    e = e.error
            return o, e
        o = pkjson.load_any(self._raw_stdout)
        return o, e

    def _subprocess_exit(self, returncode):
        async def do():
            try:
                if self._in_file:
                    pkio.unchecked_remove(self._in_file)
                    self._in_file = None
                self._parsed_stdout, self._parsed_stderr = await self._load_output()
                if returncode != 0 and not self._parsed_stderr:
                    self._parsed_stderr = 'error returncode {}'.format(
                        returncode)
                if self._parsed_stderr or returncode != 0:
                    if 'Traceback' in self._parsed_stderr:
                        pkdlog('\n{}', self._parsed_stderr)
                    else:
                        pkdlog('error={}', self._parsed_stderr)
            except Exception as e:
                self._parsed_stderr = 'error={}'.format(e)
                pkdlog(self._parsed_stderr)
            finally:
                self._subprocess_exit_event.set()
        tornado.ioloop.IOLoop.current().add_callback(do)

    def _subprocess_env(self):
        env = PKDict(os.environ)
        pkcollections.unchecked_del(
            env,
            *(k for k in env if _EXEC_ENV_REMOVE.search(k)),
        )
        env.SIREPO_MPI_CORES = str(mpi.cfg.cores)
        env.PYENV_VERSION = 'py2'
        return env


class _Process(PKDict):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.compute_job_info = None
        self.compute_job_info_file = None
        self._background_job_process = None
        self._main_job_process = None
        self._terminating = False

    def start(self):
        if self.msg.jobProcessCmd == 'compute':
            self._write_compute_job_info_file(job.Status.RUNNING.value)
        self._execute_main_job_process()
        # TODO(e-carlin): one compute if
        if self.msg.jobProcessCmd == 'compute':
            # TODO(e-carlin): Is calling simulation_db here valid?
            if simulation_db.is_parallel(self.msg.data):
                self._execute_background_percent_complete_job_process()

    def _execute_background_percent_complete_job_process(self):
        m = self.msg.copy()
        m.update(jobProcessCmd='background_percent_complete')
        m.pop('opId', None)

        async def do():
            while True:
                try:
                    self._background_job_process = _JobProcess(m)
                    self._background_job_process.start()
                    o, e = await self._background_job_process.exit()
                    if e:
                        await self.comm.write_message(
                            m,
                            job.OP_ERROR,
                            error=e,
                            output=o
                        )
                    else:
                        await self.comm.write_message(
                            m,
                            job.OP_BACKGROUND_PERCENT_COMPLETE,
                            output=o,
                        )
                except Exception as e:
                    pkdlog('error={}', e)
                finally:
                    # TODO(e-carlin): If terminating then don't start again
                    # TODO(e-carlin): make 2 configurable
                    await tornado.gen.sleep(2)
                    # TODO(e-carlin): kill this when 100% complete
        tornado.ioloop.IOLoop.current().add_callback(do)

    def _execute_main_job_process(self):
        self._main_job_process = _JobProcess(msg=self.msg)
        self._main_job_process.start()
        tornado.ioloop.IOLoop.current().add_callback(
            self._handle_main_job_process_exit
        )

    async def _handle_main_job_process_exit(self):
        try:
            o, e = await self._main_job_process.exit()
            # TODO(e-carlin): read simulation_db.read_result() or format subprocess_error
            self._main_job_process = None
            self.comm.remove_process(self.msg.jid)
            if self._terminating:  # TODO(e-carlin): why?
                return
            self._done(
                job.Status.ERROR.value if e else job.Status.COMPLETED.value)
            if e:
                o.pop('state', None)
                await self.comm.write_message(
                    self.msg,
                    job.OP_ERROR,
                    error=e,
                    output=PKDict(**o, state=job.Status.ERROR.value),
                )
            elif self.msg.jobProcessCmd == 'compute':
                o.pop('state', None)
                await self.comm.write_message(
                    self.msg,
                    job.OP_OK,
                    output=PKDict(**o, state=job.Status.COMPLETED.value),
                )
            elif self.msg.jobProcessCmd == 'compute_status':
                await self.comm.write_message(
                    self.msg,
                    job.OP_COMPUTE_STATUS,
                    output=o,
                )
            else:
                await self.comm.write_message(
                    self.msg,
                    job.OP_ANALYSIS,
                    output=o,
                )
        except Exception as exc:
            pkdlog('error={}', exc)
            try:
                await self.comm.write_message(self.msg, job.OP_ERROR, error=e, output=o)
            except Exception as exc:
                pkdlog('error={}', exc)

    def _write_compute_job_info_file(self, state):
        self.compute_job_info_file = self.msg.runDir.join(_INFO_FILE)
        pkio.mkdir_parent_only(self.compute_job_info_file)
        self.compute_job_info = PKDict(_INFO_FILE_COMMON).update(
            computeJobHash=self.msg.computeJobHash,
            startTime=time.time(),
            state=state,
        )
        # TODO(robnagler) pkio.atomic_write?
        self.compute_job_info_file.write(self.compute_job_info)

    # async def cancel(self, run_dir):
    #     # TODO(e-carlin): cancel background_sp
    #     if not self._terminating:
    #         # Will resolve itself, b/c harmless to call proc.kill
    #         tornado.ioloop.IOLoop.current().call_later(
    #             _TERMINATE_SECS,
    #             self._kill,
    #         )
    #         self._terminating = True
    #         self._done(job.Status.CANCELED.value)
    #         self._main_sp.proc.terminate()

    def kill(self):
        # TODO(e-carlin): kill background_sp
        self._terminating = True
        if self._main_job_process:
            self._done(job.Status.CANCELED.value)
            self._main_job_process.kill()
            self._main_job_process = None

    def _done(self, status):
        if self.compute_job_info_file:
            self.compute_job_info.status = status
            self.compute_job_info_file.write(self.compute_job_info.status)
            self.compute_job_info_file = None


class _Comm(PKDict):

    def kill(self):
        x = list(self._processes.values())
        self._processes = PKDict()
        for p in x:
            p.kill()
        tornado.ioloop.IOLoop.current().stop()

    async def loop(self):
        self._processes = PKDict()

        while True:
            try:
                self._websocket = None
                try:
                    # TODO(robnagler) connect_timeout, max_message_size, ping_interval, ping_timeout
                    c = await tornado.websocket.websocket_connect(cfg.supervisor_uri)
                    self._websocket = c
                except ConnectionRefusedError as e:
                    pkdlog('error={}', e)
                    await tornado.gen.sleep(_RETRY_SECS)
                    continue
                m = self._format_reply(None, job.OP_OK)
                while True:
                    try:
                        if m:
                            await self._websocket.write_message(m)
                    except tornado.websocket.WebSocketClosedError as e:
                        pkdlog('error={}', e)
                        break
                    m = await c.read_message()
                    pkdc('msg={}', job.LogFormatter(m))
                    if m is None:
                        break
                    m = await self._op(m)
            except Exception as e:
                pkdlog('error={} \n{}', e, pkdexc())

    def remove_process(self, jid):
        assert jid in self._processes
        del self._processes[jid]

    async def write_message(self, msg, op, **kwargs):
        try:
            await self._websocket.write_message(self._format_reply(msg, op, **kwargs))
        except Exception as e:
            pkdlog('error={}', e)

    def _format_reply(self, msg, op, **kwargs):
        if msg:
            kwargs['opId'] = msg.get('opId')
            kwargs['jid'] = msg.get('jid')
        return pkjson.dump_bytes(
            PKDict(agentId=cfg.agent_id, op=op, **kwargs),
        )

    async def _op(self, msg):
        try:
            m = pkjson.load_any(msg)
            m.runDir = pkio.py_path(m.runDir)
            r = await getattr(self, '_op_' + m.op)(m)
            if r:
                r = r if isinstance(
                    r, bytes) else self._format_reply(m, job.OP_OK)
                return r
            return None
        except Exception as e:
            err = 'exception=' + str(e)
            stack = pkdexc()
            pkdlog('{} \n{}', err, stack)
            return self._format_reply(None, job.OP_ERROR, error=err, stack=stack)

    async def _op_cancel(self, msg):
        p = self._processes.get(msg.jid)
        if not p:
            return self._format_reply(msg, job.OP_ERROR, error='no such jid')
        await p.cancel()  # TODO(e-carlin): cancel should be sync fire and forget
        return True

    async def _op_compute_status(self, msg):
        assert msg.jid not in self._processes, \
            "jid={} in processes. Supervisor should already now about status".format(
                msg.jid)
        try:
            i = pkjson.load_any(msg.runDir.join(_INFO_FILE))
            return self._format_reply(
                msg,
                job.OP_COMPUTE_STATUS,
                output=PKDict(
                    state=i.state,
                    computeJobHash=i.computeJobHash,
                ),
            )
        except Exception:
            f = msg.runDir.join(job.RUNNER_STATUS_FILE)
            if f.check():
                assert msg.jid not in self._processes
                msg.update(jobProcessCmd='compute_status')
                self._process(msg)
                return False
        return self._format_reply(
            msg,
            job.OP_COMPUTE_STATUS,
            output=PKDict(state=job.Status.MISSING.value),
        )

    async def _op_kill(self, msg):
        self.kill()
        return True

    async def _op_result(self, msg):
        msg.update(jobProcessCmd='result')
        self._process(msg)
        return False

    async def _op_run(self, msg):
        m = msg.copy()
        del m['opId']
        m.update(jobProcessCmd='compute')
        self._process(m)
        return self._format_reply(
            msg,
            job.OP_OK,
            output=PKDict(
                state=job.Status.RUNNING.value,
                computeJobHash=msg.computeJobHash,
            ),
        )

    async def _op_analysis(self, msg):
        if msg.jobProcessCmd == 'background_percent_complete':
            if not msg.runDir.exists():
                return self._format_reply(
                    msg,
                    job.OP_OK,
                    output=PKDict(
                        percentComplete=0.0,
                        frameCount=0,
                    ),
                )
        self._process(msg)
        return False

    def _process(self, msg):
        p = _Process(msg=msg, comm=self)
        assert msg.jid not in self._processes
        self._processes[msg.jid] = p
        p.start()
