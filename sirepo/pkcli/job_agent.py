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
from pykern.pkdebug import pkdlog, pkdp, pkdexc, pkdc
from sirepo import job, mpi, simulation_db
from sirepo.pkcli import job_process
import json
import os
import re
import signal
import subprocess
import sys
import time
import tornado.gen
import tornado.ioloop
import tornado.locks
import tornado.process
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
    job.init()
    global cfg

    cfg = pkconfig.init(
        agent_id=pkconfig.Required(str, 'id of this agent'),
        supervisor_uri=pkconfig.Required(
            str,
            'how to connect to the supervisor',
        ),
    )
    pkdlog('{}', cfg)
    i = tornado.ioloop.IOLoop.current()
    c = _Comm()
    def s(n, x): return i.add_callback_from_signal(c.terminate)
    signal.signal(signal.SIGTERM, s)
    signal.signal(signal.SIGINT, s)
    i.spawn_callback(c.loop)
    i.start()


class _Comm(PKDict):

    async def loop(self):
        while True:
            try:
                self._websocket = None
                try:
#TODO(robnagler) connect_timeout, max_message_size, ping_interval, ping_timeout
                    c = await tornado.websocket.websocket_connect(cfg.supervisor_uri)
                    self._websocket = c
                except ConnectionRefusedError as e:
                    pkdlog('error={}', e)
                    await tornado.gen.sleep(_RETRY_SECS)
                    continue
                m = self._format_op(None, job.OP_ALIVE)
                while True:
                    if m and not await self.send(m):
                        break
                    m = await c.read_message()
                    pkdc('msg={}', job.LogFormatter(m))
                    if m is None:
                        break
                    m = await self._op(m)
            except Exception as e:
                pkdlog('error={} stack={}', e, pkdexc())

    async def send(self, msg):
        try:
            await self._websocket.write_message(msg)
            return True
        except Exception as e:
            pkdlog('msg={} error={}', job.LogFormatter(msg), e)
            return False

    def terminate(self):
        pass

    def _format_op(self, msg, opName, **kwargs):
        if msg:
            kwargs['opId'] = msg.get('opId')
            kwargs['computeJid'] = msg.get('computeJid')
        return pkjson.dump_bytes(
            PKDict(agentId=cfg.agent_id, opName=opName, **kwargs),
        )

    async def _op(self, msg):
        m = None
        try:
            m = pkjson.load_any(msg)
            m.runDir = pkio.py_path(m.runDir)
            return await getattr(self, '_op_' + m.opName)(m)
        except Exception as e:
            err = 'exception=' + str(e)
            stack = pkdexc()
            pkdlog('{} stack={}', err, stack)
            return self._format_op(m, job.OP_ERROR, error=err, stack=stack)

    async def _op_cancel(self, msg):
        p = self._processes.get(msg.computeJid)
        if not p:
            return self._format_op(msg, job.OP_ERROR, error='no such computeJid')
        # TODO(e-carlin): cancel should be sync fire and forget
        await p.cancel()
        return self._format_op(msg, job.OP_OK)

    async def _op_kill(self, msg):
        self.kill()
        return self._format_op(msg, job.OP_OK)

    async def _op_run(self, msg):
        self._process(msg)
        return None

    async def _op_analysis(self, msg):
        self._process(msg)
        return None

    def _process(self, msg):
        p = _Process(msg=msg, comm=self)
#TODO(robnagler) there should only be one computeJid per agent.
#   background_percent_complete is not an analysis
        assert msg.computeJid not in self._processes
        self._processes[msg.computeJid] = p
        p.start()


class _JobProcess(PKDict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._subprocess = None
        self._in_file = None
        self._subprocess_exit_event = tornado.locks.Event()

    async def exit_ready(self):
        await self._exit_ready.wait()
        await self._stdout.ready.wait()
        await self._stderr.ready.wait()

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
        self._stdout = _Stream(self._subprocess.stdout)
        self._stderr = _Stream(self._subprocess.stderr)
        self._exit_ready = tornado.locks.Event()
        self._subprocess.set_exit_callback(self._subprocess_exit)

    async def _load_output(self):
        o = None
        e = None
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
            return o, e
        o = pkjson.load_any(self._raw_stdout)
        return o, e

    def _subprocess_exit(self, returncode):
        async def do():
            if self._in_file:
                pkio.unchecked_remove(self._in_file)
                self._in_file = None
            self.returncode = returncode
            self._subprocess_exit_event.set()
        tornado.ioloop.IOLoop.current().add_callback(do)

    def _subprocess_env(self):
        env = PKDict(os.environ)
        pkcollections.unchecked_del(
            env,
            *(k for k in env if _EXEC_ENV_REMOVE.search(k)),
        )
        return env.pkupdate(
#TODO(robnagler) mpi.cores will not be defined
            SIREPO_MPI_CORES=str(mpi.cfg.cores),
            PYENV_VERSION='py2',
        )

class _Stream(PKDict):
    _MAX = int(1e8)

    def __init__(self, stream):
        super().__init__(
            stream=stream,
            ready=tornado.locks.Event(),
            text=bytearray(),
            too_large=False,
        )
        tornado.ioloop.IOLoop.current().add_callback(self._read)

    async def _read(self):
        while True:
            await self.stream.read_into(self.text, partial=True)
            if self.stream.closed():
                break
            if len(self.text) > self._MAX:
                self.too_large = True
                self.stream.close()
                break
        self.ready.set()


class _Process(PKDict):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._background_job_process = None
        self._main_job_process = None
        self._terminating = False

    def start(self):
        self._main_job_process = _JobProcess(msg=self.msg)
        self._main_job_process.start()
        tornado.ioloop.IOLoop.current().add_callback(
            self._handle_main_job_process_exit
        )

    async def _handle_main_job_process_exit(self):
        try:
            await self._main_job_process.exit_ready()
            # TODO(e-carlin): read simulation_db.read_result() or format subprocess_error
            self._main_job_process = None
            if self._terminating:  # TODO(e-carlin): why?
                return
            self._done(job.ERROR if e else job.COMPLETED)
            if e:
                o.state = job.ERROR
                await self.comm.write_message(
                    self.msg,
                    job.OP_ERROR,
                    error=e,
                    reply=PKDict(**o),
                )
#TODO(robnagler) answer cancel
            elif self.msg.jobProcessCmd == 'compute':
                await self.comm.write_message(
                    self.msg,
                    job.OP_RUN,
                    reply=PKDict(**o),
                )
            else:
                await self.comm.write_message(
                    self.msg,
                    job.OP_ANALYSIS,
                    reply=o,
                )
        except Exception as exc:
            pkdlog('error={}', exc)
            try:
                await self.comm.write_message(self.msg, job.OP_ERROR, error=e, reply=o)
            except Exception as exc:
                pkdlog('error={}', exc)
