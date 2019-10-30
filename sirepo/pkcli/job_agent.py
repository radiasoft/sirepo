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
import tornado.iostream
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
    d = _Dispatcher()
    def s(n, x):
        return i.add_callback_from_signal(d.terminate)
    signal.signal(signal.SIGTERM, s)
    signal.signal(signal.SIGINT, s)
    i.spawn_callback(d.loop)
    i.start()


class _Dispatcher(PKDict):
    processes = PKDict()

    async def loop(self):
        while True:
            self._websocket = None
            try:
#TODO(robnagler) connect_timeout, max_message_size, ping_interval, ping_timeout
                self._websocket = await tornado.websocket.websocket_connect(
                    cfg.supervisor_uri,
                )
                m = self.format_op(None, job.OP_ALIVE)
                while True:
                    if m and not await self.send(m):
                        break
                    m = await self._websocket.read_message()
                    if m is None:
                        break
                    m = await self._op(m)
            except ConnectionRefusedError as e:
                await tornado.gen.sleep(_RETRY_SECS)
            except Exception as e:
                pkdlog('error={} stack={}', e, pkdexc())
            finally:
                if self._websocket:
                    self._websocket.close()

    async def send(self, msg):
        try:
            await self._websocket.write_message(msg)
            return True
        except Exception as e:
            pkdlog('msg={} error={}', job.LogFormatter(msg), e)
            return False

    def terminate(self):
#TODO(robnagler) kill all processes
        pass

    def format_op(self, msg, opName, **kwargs):
        if msg:
            kwargs['opId'] = msg.get('opId')
            # kwargs['computeJid'] = msg.get('computeJid')
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
            return self.format_op(m, job.OP_ERROR, error=err, stack=stack)

    async def _op_cancel(self, msg):
        p = self.processes.get(msg.computeJid)
        if not p:
            return self.format_op(msg, job.OP_ERROR, error='no such computeJid')
        await p.cancel()
        return self.format_op(msg, job.OP_OK)

    async def _op_kill(self, msg):
        self.send(self.format_op(msg, job.OP_OK))
        self.kill()
        return None

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
        assert msg.computeJid not in self.processes
        self.processes[msg.computeJid] = p
        p.start()


class _Job(PKDict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._subprocess = None
        self._in_file = None
        self._subprocess_exit_event = tornado.locks.Event()

    async def exit_ready(self):
        await self._exit.wait()
        await self.stdout.ready.wait()
        await self.stderr.ready.wait()

    def kill(self):
        # TODO(e-carlin): Terminate?
        self._subprocess.proc.kill()

    def start(self):
        # SECURITY: msg must not contain agentId
        assert not self.msg.get('agentId')
        env = self._subprocess_env()
        self._in_file = self.msg.runDir.join(
            _IN_FILE.format(job.unique_key()))
        pkio.mkdir_parent_only(self._in_file)
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
        self.stdout = _Stream(self._subprocess.stdout)
        self.stderr = _Stream(self._subprocess.stderr)
        self._exit = tornado.locks.Event()
        self._subprocess.set_exit_callback(self._subprocess_exit)

    def _subprocess_exit(self, returncode):
        if self._in_file:
            pkio.unchecked_remove(self._in_file)
            self._in_file = None
        self.returncode = returncode
        self._exit.set()

    def _subprocess_env(self):
        env = PKDict(os.environ)
        pkcollections.unchecked_del(
            env,
            *(k for k in env if _EXEC_ENV_REMOVE.search(k)),
        )
        return env.pkupdate(
            SIREPO_MPI_CORES=str(self.msg.mpiCores),
            PYENV_VERSION='py2',
        )

class _Stream(PKDict):
    _MAX = int(1e8)
    _DELIM = b'\n'

    def __init__(self, stream):
        super().__init__(
            stream=stream,
            ready=tornado.locks.Event(),
            bytes=bytearray(),
        )
        tornado.ioloop.IOLoop.current().add_callback(self._read)

    async def _read(self):
        while True:
            try:
                self.bytes.extend(
                    await self.stream.read_until(self._DELIM, self._MAX)
                )
            # raised when there is no more data on stream to read
            except tornado.iostream.StreamClosedError as e:
                assert e.real_error is None, 'error={}'.format(e.real_error)
                break
        self.ready.set()


class _Process(PKDict):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        t = time.time()
        self.pkupdate(
            startTime=t,
            lastUpdateTime=t,
            _background_job_process=None,
            _job_proc=None,
            _terminating=False,
            **kwargs,
        )

    def start(self):
        self._job_proc = _Job(msg=self.msg)
        self._job_proc.start()
        tornado.ioloop.IOLoop.current().add_callback(
            self._handle_job_proc_exit
        )


    async def _handle_job_proc_exit(self):
        try:
            await self._job_proc.exit_ready()
            if self._terminating:
                return
            del self.comm.processes[self.msg.computeJid]
            e = self._job_proc.stderr.bytes.decode('utf-8', errors='ignore')
            r = pkjson.load_any(self._job_proc.stdout.bytes)
            if self._job_proc.returncode != 0:
                await self.comm.send(
                    self.comm.format_op(
                        self.msg,
                        job.OP_ERROR,
                        error=e,
                        reply=r,
                    )
                )
            elif self.msg.jobProcessCmd == 'compute':
                await self.comm.send(
                    self.comm.format_op(
                        self.msg,
                        job.OP_RUN,
                        reply=r,
                    )
                )
            else:
                await self.comm.send(
                    self.comm.format_op(
                        self.msg,
                        job.OP_ANALYSIS,
                        reply=r,
                    )
                )
        except Exception as exc:
            pkdlog(
                'error={} returncode={} stderr={}',
                exc,
                self._job_proc.returncode,
                e,
            )