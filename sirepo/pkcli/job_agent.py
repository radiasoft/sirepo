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
from sirepo import job
from sirepo.pkcli import job_process
import json
import os
import re
import signal
import sirepo.auth
import sirepo.srdb
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

    def format_op(self, msg, opName, **kwargs):
        if msg:
            kwargs['opId'] = msg.get('opId')
        return pkjson.dump_bytes(
            PKDict(agentId=cfg.agent_id, opName=opName, **kwargs),
        )

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
                        raise ValueError('response from supervisor was None')
                    m = await self._op(m)
            except Exception as e:
                pkdlog('error={} stack={}', e, pkdexc())
                # TODO(e-carlin): exponential backoff?
                await tornado.gen.sleep(_RETRY_SECS)
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
        for p in self.processes.values():
            p.kill()
        self.processes.clear()
        tornado.ioloop.IOLoop.current().stop()

    async def _op(self, msg):
        m = None
        try:
            m = pkjson.load_any(msg)
            pkdc('m={}', job.LogFormatter(m))
            if 'runDir' in m:
                m.runDir = pkio.py_path(m.runDir)
            return await getattr(self, '_op_' + m.opName)(m)
        except Exception as e:
            err = 'exception=' + str(e)
            stack = pkdexc()
            return self.format_op(m, job.OP_ERROR, error=err, stack=stack)

    async def _op_analysis(self, msg):
        self._process(msg)
        return None

    async def _op_cancel(self, msg):
        p = self.processes.get(msg.computeJid)
        if not p:
            return self.format_op(msg, job.OP_ERROR, error='no such computeJid')
        p.kill()
        del self.processes[msg.computeJid]
        return self.format_op(msg, job.OP_OK, reply=PKDict(state=job.CANCELED, opDone=True))

    async def _op_kill(self, msg):
        try:
            for p in self.processes.values():
                p.kill()
        except Exception as e:
            pkdlog('error={} stack={}', e, pkdexc())
        finally:
            tornado.ioloop.IOLoop.current().stop()

    async def _op_run(self, msg):
        self._process(msg)
        return None

    def _process(self, msg):
        p = _JobProcess(msg=msg, comm=self)
        # p = _DockerJobProcess(msg=msg, comm=self)
#TODO(robnagler) there should only be one computeJid per agent.
#   background_percent_complete is not an analysis
        assert msg.computeJid not in self.processes
        self.processes[msg.computeJid] = p
        p.start()


class _JobProcess(PKDict):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._subprocess = _Subprocess(
                self._subprocess_cmd_stdin_env,
                self._on_stdout_read,
                msg=self.msg,
            )
        self._terminating = False

# TODO(e-carlin): rename to cancel?
    def kill(self):
        # TODO(e-carlin): terminate?
        self._terminating = True
        self._subprocess.kill()

    def start(self):
        self._subprocess.start()
        tornado.ioloop.IOLoop.current().add_callback(
            self._on_exit
        )

    def _subprocess_cmd_stdin_env(self, in_file):
        return job.subprocess_cmd_stdin_env(
            ('sirepo', 'job_process', in_file),
            PKDict(
                PYTHONUNBUFFERED='1',
                SIREPO_AUTH_LOGGED_IN_USER=sirepo.auth.logged_in_user(),
                SIREPO_MPI_CORES=self.msg.mpiCores,
                SIREPO_SIM_LIB_FILE_URI=self.msg.get('libFileUri', ''),
                SIREPO_SRDB_ROOT=sirepo.srdb.root(),
            ),
            pyenv='py2',
        )

    async def _on_stdout_read(self, text):
        if self._terminating:
            return
        try:
            r = pkjson.load_any(text)
            if 'opDone' in r:
                del self.comm.processes[self.msg.computeJid]
            if self.msg.jobProcessCmd == 'compute':
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
            pkdlog('error=={}', exc)

    async def _on_exit(self):
        try:
            await self._subprocess.exit_ready()
            if self._terminating:
                await self.comm.send(
                    self.comm.format_op(
                        self.msg,
                        job.OP_OK,
                        reply=PKDict(state=job.CANCELED, opDone=True),
                    )
                )
                return
            e = self._subprocess.stderr.text.decode('utf-8', errors='ignore')
            if e:
                pkdlog('error={}', e)
            if self._subprocess.returncode != 0:
                await self.comm.send(
                    self.comm.format_op(
                        self.msg,
                        job.OP_ERROR,
                        opDone=True,
                        error=e,
                        reply=PKDict(
                            state=job.ERROR,
                            error='returncode={}'.format(self._subprocess.returncode)),
                    )
                )
        except Exception as exc:
            pkdlog('error={} returncode={}', exc, self._subprocess.returncode)


class _DockerJobProcess(_JobProcess):

    def _subprocess_cmd_stdin_env(self, in_file):
        # The volumes mounted and no cascading of env is problematic for docker. Docker is
        # is going to be replaced with singulatiry which doesn't have these problems so
        # it is fine for now
        return job.subprocess_cmd_stdin_env(
            (
                'docker',
                'run',
                '--interactive',
                '--volume=/home/vagrant/src/radiasoft/sirepo/sirepo:/home/vagrant/.pyenv/versions/2.7.16/envs/py2/lib/python2.7/site-packages/sirepo',
                '--volume=/home/vagrant/src/radiasoft/pykern/pykern:/home/vagrant/.pyenv/versions/2.7.16/envs/py2/lib/python2.7/site-packages/pykern',
                '--volume={}:{}'.format(self.msg.runDir, self.msg.runDir),
                '--workdir={}'.format(self.msg.runDir),
                'radiasoft/sirepo:dev',
                '/bin/bash',
                '-l',
                '-c',
                'sirepo job_process {}'.format(in_file),
            ),
            PKDict())


class _Stream(PKDict):
    _MAX = int(1e8)

    def __init__(self, stream):
        super().__init__(
            stream_closed=tornado.locks.Event(),
            text=bytearray(),
            _stream=stream,
        )
        tornado.ioloop.IOLoop.current().add_callback(self._begin_read_stream)

    async def _begin_read_stream(self):
        try:
            while True:
                await self._read_stream()
        except tornado.iostream.StreamClosedError as e:
            assert e.real_error is None, 'real_error={}'.format(e.real_error)
        finally:
            self._stream.close()
            self.stream_closed.set()

    async def _read_stream(self):
        raise NotImplementedError()


class _Subprocess(PKDict):
    def __init__(self, subprocess_cmd_stdin_env, on_stdout_read,  *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.update(
            stderr=None,
            stdout=None,
            _exit=tornado.locks.Event(),
            _in_file=None,
            _on_stdout_read=on_stdout_read,
            _subprocess=None,
            _subprocess_cmd_stdin_env=subprocess_cmd_stdin_env,
        )

    async def exit_ready(self):
        await self._exit.wait()
        await self.stdout.stream_closed.wait()
        await self.stderr.stream_closed.wait()

    def kill(self):
        # TODO(e-carlin): Terminate?
        os.killpg(self._subprocess.proc.pid, signal.SIGKILL)

    def _create_in_file(self):
        self._in_file = self.msg.runDir.join(
            _IN_FILE.format(job.unique_key()),
        )
        pkio.mkdir_parent_only(self._in_file)
        pkjson.dump_pretty(self.msg, filename=self._in_file, pretty=False)

    def start(self):
        # SECURITY: msg must not contain agentId
        assert not self.msg.get('agentId')
        self._create_in_file()
        # TODO(e-carlin): Find a better solution for serial and deserialization
        self.msg.runDir = str(self.msg.runDir)
        cmd, stdin, env = self._subprocess_cmd_stdin_env(self._in_file)
        self._subprocess = tornado.process.Subprocess(
            cmd,
            cwd=self.msg.runDir,
            env=env,
            start_new_session=True, # TODO(e-carlin): generalize?
            stdin=stdin,
            stdout=tornado.process.Subprocess.STREAM,
            stderr=tornado.process.Subprocess.STREAM,
        )
        stdin.close()
        self.stdout = _ReadJsonlStream(self._subprocess.stdout, self._on_stdout_read)
        self.stderr = _ReadUntilCloseStream(self._subprocess.stderr)
        self._subprocess.set_exit_callback(self._on_exit)

    def _on_exit(self, returncode):
        if self._in_file:
            pkio.unchecked_remove(self._in_file)
            self._in_file = None
        self.returncode = returncode
        self._exit.set()


class _ReadJsonlStream(_Stream):
    def __init__(self, stream, on_read):
        self._on_read = on_read
        self.proceed_with_read = tornado.locks.Condition()
        self.read_occurred = tornado.locks.Condition()
        super().__init__(stream)

    async def _read_stream(self):
        self.text = await self._stream.read_until(b'\n', self._MAX)
        pkdc('stdout={}', self.text[:1000])
        await self._on_read(self.text)


class _ReadUntilCloseStream(_Stream):
    def __init__(self, stream):
        super().__init__(stream)

    async def _read_stream(self):
        t = await self._stream.read_bytes(
            self._MAX - len(self.text),
            partial=True,
        )
        pkdc('stderr={}', t)
        l = len(self.text) + len(t)
        assert l < self._MAX, \
            'len(bytes)={} greater than _MAX={}'.format(l, _MAX)
        self.text.extend(t)
