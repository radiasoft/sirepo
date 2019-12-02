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
from sirepo.template import template_common
import json
import os
import re
import signal
import sirepo.auth
import sirepo.srdb
import subprocess
import sys
import time
import tornado.gen
import tornado.ioloop
import tornado.iostream
import tornado.locks
import tornado.process
import tornado.websocket


#: Long enough for job_cmd to write result in run_dir
_TERMINATE_SECS = 3

_RETRY_SECS = 1

_IN_FILE = 'in-{}.json'


cfg = None


def default_command():
#TODO(robnagler) commands need their own init hook like the server has
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
    cmds = []

    def cmd_exit(self, cmd):
        try:
            self.cmds.remove(cmd)
        except Exception:
            pass

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
        c = self.cmds
        self.cmds = []
        for p in c:
            p.kill()
        tornado.ioloop.IOLoop.current().stop()

    async def _op(self, msg):
        m = None
        try:
            m = pkjson.load_any(msg)
            pkdc('m={}', job.LogFormatter(m))
            return await getattr(self, '_op_' + m.opName)(m)
        except Exception as e:
            err = 'exception=' + str(e)
            stack = pkdexc()
            return self.format_op(m, job.OP_ERROR, error=err, stack=stack)

    async def _op_analysis(self, msg):
        return self._cmd(msg)

    async def _op_cancel(self, msg):
        for c in self.cmds:
            if c.jid == msg.computeJid:
                c.kill()
                self.cmd_exit(c)
        return self.format_op(msg, job.OP_OK, reply=PKDict(state=job.CANCELED))

    async def _op_kill(self, msg):
        try:
            x = self.cmds
            self.cmds = []
            for c in x:
                try:
                    c.kill()
                except Exception as e:
                    pkdlog('cmd={} error={} stack={}', c, e, pkdexc())
        finally:
            tornado.ioloop.IOLoop.current().stop()

    async def _op_run(self, msg):
        return self._cmd(msg)

    def _cmd(self, msg):
        c = _Cmd
        if msg.jobRunMode == job.SBATCH:
            c = _SbatchRun if msg.isParallel else _SbatchProcess
        p = c(msg=msg, dispatcher=self)
        self.cmds.append(p)
        p.start()
        return None


class _Cmd(PKDict):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._in_file = self._create_in_file()
        self._process = _Process(self)
        self._terminating = False
        self._start_time = int(time.time())
        self._is_compute = self.msg.jobCmd == 'compute'
        self.jid = self.msg.computeJid
        self.run_dir = pkio.py_path(self.msg.runDir)

    def job_cmd_cmd_stdin_env(self):
        return job.subprocess_cmd_stdin_env(
            ('sirepo', 'job_cmd', self._in_file),
            env=self.job_cmd_env(),
            pyenv=self.job_cmd_pyenv(),
        )

    def job_cmd_env(self):
        return job.subprocess_env(
            env=PKDict(
                SIREPO_MPI_CORES=self.msg.mpiCores,
                SIREPO_SIM_LIB_FILE_URI=self.msg.get('libFileUri', ''),
            ),
        )

    def job_cmd_pyenv(self):
        return 'py2'

    def kill(self):
        self._terminating = True
        self._process.kill()

    async def on_stdout_read(self, text):
        if self._terminating:
            return
        try:
            r = pkjson.load_any(text)
            if r.state in job.EXIT_STATUSES:
                self.dispatcher.cmd_exit(self)
            o = job.OP_ANALYSIS
            if self._is_compute:
                if 'computeJobStart' in r:
                    self._start_time = r.computeJobStart
                o = job.OP_RUN
            await self.dispatcher.send(
                self.dispatcher.format_op(self.msg, o, reply=r)
            )
        except Exception as exc:
            pkdlog('error=={}', exc)

    def start(self):
        self._process.start()
        if self._is_compute and self._start_time:
            await self.dispatcher.send(
                self.dispatcher.format_op(
                    self.msg,
                    job.OP_RUN,
                    reply=PKDict(state=job.RUNNING, computeJobStart=self._start_time),
                ),
            )
        tornado.ioloop.IOLoop.current().add_callback(self._await_exit)

    async def _await_exit(self):
        try:
            await self._process.exit_ready()
            if self._in_file:
                pkio.unchecked_remove(self._in_file)
                self._in_file = None
            if 'dispatcher' not in self:
                return
            self.dispatcher.cmd_exit()
            if self._terminating:
                await self.dispatcher.send(
                    self.dispatcher.format_op(
                        self.msg,
                        job.OP_OK,
                        reply=PKDict(state=job.CANCELED),
                    )
                )
                return
            e = self._process.stderr.text.decode('utf-8', errors='ignore')
            if e:
                pkdlog('error={}', e)
            if self._process.returncode != 0:
                await self.dispatcher.send(
                    self.dispatcher.format_op(
                        self.msg,
                        job.OP_ERROR,
                        error=e,
                        reply=PKDict(
                            state=job.ERROR,
                            error=f'process exit={self._process.returncode} jid={self.jid}',
                        ),
                    )
                )
        except Exception as exc:
            pkdlog('jid={} error={} returncode={}', self.jid, exc, self._process.returncode)

    def _create_in_file(self):
        f = self.run_dir.join(
            _IN_FILE.format(job.unique_key()),
        )
        pkio.mkdir_parent_only(f)
        pkjson.dump_pretty(self.msg, filename=f, pretty=False)
        return f


class _SbatchCmd(_Cmd):

#TODO(robnagler) insert shifter
    async def exited(self):
        await self._process.exit_ready()


class _SbatchParallelStatus(_SbatchCmd):

    async def _await_exit(self):
        await self._process.exit_ready()
        if self._terminating:
            e = self._process.stderr.text.decode('utf-8', errors='ignore')
            if e:
                pkdlog('error={} jid={}', e, self.jid)
            return
        else:
            # TODO(e-carlin): We should restart the job if this happens
            pkdlog('error: exited without a termination request')


class _SbatchRun(_Cmd):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._start_time = 0
        self._sbatch_id = None
        self.run_dir = pkio.mkdir_parent(self.msg.runDir)

    def kill(self):
        if self._sbatch_id is not None:
            subprocess.check_call(
                ('scancel', '--full', '--quiet', self._sbatch_id)
            )
        self.msg.sbatchId = self._sbatch_id
        super().kill(self)

    def start(self):
        self._sbatch_id =  self._submit_compute_to_sbatch(
            self._prepare_simulation(),
        )
        super().start()

    def _sbatch_script(self):
        return f'''
#SBATCH --constraint=haswell
#SBATCH --error={template_common.RUN_LOG}
#SBATCH --ntasks={self.msg.sbatchCores}
#SBATCH --output={template_common.RUN_LOG}
#SBATCH --qos=debug
#SBATCH --tasks-per-node=32
#SBATCH --time={self._sbatch_time()}
{'#SBATCH --image=self.msg.shifterImage' if self.msg.shifterImage else ''}

srun --cpu-bind=cores shifter /bin/bash <<'EOF'
export HOME=/home/vagrant; source /home/vagrant/.bashrc; eval export HOME=~$USER
# this may not be necessary
{self.job_cmd_env()}
pyenv shell {self.job_cmd_pyenv()}
python template_common.PARAMETERS_PYTHON_FILE
EOF
'''

    def _sbatch_time(self):
#TODO(robnagler) msg.sbatchHours is a float to be converted
        return round(
            datetime.timedelta(
                hours=float(self.msg.sbatchHours)
            ).total_seconds() / 60,
        )

    def _prepare_simulation(self):
        c = _SBatchCmd(msg=self.msg.copy().pkupdate(
            runDir=self.run_dir,
            jobCmd='prepare_simulation'),
        )
        c.start()
        return pkjson.load_any(r).cmd

    async def _start_compute(self):
        await self._await_job_completion_and_parallel_status(
                self._sbatch_id,
            )
        except Exception as e:
            # POSIT: jobCmd is the only field every changed in msg
            await self.dispatcher.send(
                self.dispatcher.format_op(
                    self.msg,
                    job.OP_ERROR,
                    reply=PKDict(
                        state=job.ERROR,
                        error=str(e),
                        stack=pkdexc(),
                    ),
                ),
            )

    def _submit_compute_to_sbatch(self):
        s = self._sbatch_script()
        subprocess.check_output(
            ('scancel', '--full', '--quiet', self._sbatch_id),
        )

        n = str(self.run_dir.join('sbatch.in'))
        try:
            with open(n, 'w+') as f:
                f.write(s)
                f.seek(0)
                o = subprocess.check_output(
                    ('sbatch'),
                    stdin=f,
                    stderr=subprocess.STDOUT,
                ).decode('UTF-8')
                r = re.search(r'\d+$', o)
                assert r is not None, 'output={} did not cotain job id'.format(o)
                return r.group()
        except subprocess.CalledProcessError as e:
            pkdlog('error: returncode={} output={}', e.returncode, e.output)
            raise


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


class _Process(PKDict):
    def __init__(self, cmd):
        super().__init__(*args, **kwargs)
        self.update(
            stderr=None,
            stdout=None,
            cmd=cmd,
            _exit=tornado.locks.Event(),
            _in_file=None,
            _subprocess=None,
        )

    async def exit_ready(self):
        await self._exit.wait()
        await self.stdout.stream_closed.wait()
        await self.stderr.stream_closed.wait()

    def kill(self):
        # TODO(e-carlin): Terminate?
        os.killpg(self._subprocess.proc.pid, signal.SIGKILL)

    def start(self):
        # SECURITY: msg must not contain agentId
        assert not self.msg.get('agentId')
        c, s, e = self.cmd.job_cmd_cmd_stdin_env()
        self._subprocess = tornado.process.Subprocess(
            c,
            cwd=str(self.cmd.run_dir),
            env=e,
            start_new_session=True, # TODO(e-carlin): generalize?
            stdin=s,
            stdout=tornado.process.Subprocess.STREAM,
            stderr=tornado.process.Subprocess.STREAM,
        )
        s.close()
        self.stdout = _ReadJsonlStream(self._subprocess.stdout, self.cmd)
        self.stderr = _ReadUntilCloseStream(self._subprocess.stderr)
        self._subprocess.set_exit_callback(self._on_exit)
        return self

    def _on_exit(self, returncode):
        self.returncode = returncode
        self._exit.set()


class _ReadJsonlStream(_Stream):
    def __init__(self, stream, cmd):
        self.proceed_with_read = tornado.locks.Condition()
        self.read_occurred = tornado.locks.Condition()
        super().__init__(stream)

    async def _read_stream(self):
        self.text = await self._stream.read_until(b'\n', self._MAX)
        pkdc('stdout={}', self.text[:1000])
        await self.cmd.on_stdout_read(self.text)


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
