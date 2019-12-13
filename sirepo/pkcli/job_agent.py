# -*- coding: utf-8 -*-
"""Agent for managing the execution of jobs.

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern import pkcollections
from pykern import pkconfig
from pykern import pkio
from pykern import pkjson
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdlog, pkdp, pkdexc, pkdc
from sirepo import job
from sirepo.template import template_common
import datetime
import json
import os
import re
import signal
import sirepo.auth
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
    def __init__(self):
        super().__init__()
        self.cmds = []

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
        if not self._websocket:
            return False
        try:
            await self._websocket.write_message(msg)
            return True
        except Exception as e:
            pkdlog('msg={} error={}', job.LogFormatter(msg), e)
            return False

    def terminate(self):
        try:
            x = self.cmds
            self.cmds.clear()
            for c in x:
                try:
                    c.destroy()
                except Exception as e:
                    pkdlog('cmd={} error={} stack={}', c, e, pkdexc())
            return None
        finally:
            tornado.ioloop.IOLoop.current().stop()

    async def _op(self, msg):
        m = None
        try:
            m = pkjson.load_any(msg)
            pkdlog('op={} opId={} shifterImage={}', m.opName, m.get('opId'), m.get('shifterImage'))
            pkdc('m={}', job.LogFormatter(m))
            return await getattr(self, '_op_' + m.opName)(m)
        except Exception as e:
            err = 'exception=' + str(e)
            stack = pkdexc()
            pkdlog(
                'op={} exception={} stack={}',
                m and m.get('opName'),
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
        for c in self.cmds:
            if c.jid == msg.computeJid:
                c.destroy()
        return None

    async def _op_kill(self, msg):
        self.terminate()
        return None

    async def _op_run(self, msg):
        return await self._cmd(msg)

    async def _cmd(self, msg):
        c = _Cmd
        if msg.jobRunMode == job.SBATCH:
            c = _SbatchRun if msg.isParallel else _SbatchCmd
        p = c(msg=msg, dispatcher=self)
        self.cmds.append(p)
        await p.start()
        return None


class _Cmd(PKDict):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.run_dir = pkio.py_path(self.msg.runDir)
        self._is_compute = self.msg.jobCmd == 'compute'
        if self._is_compute:
            pkio.unchecked_remove(self.run_dir)
            pkio.mkdir_parent(self.run_dir)
        self._in_file = self._create_in_file()
        self._process = _Process(self)
        self._terminating = False
        self._start_time = int(time.time())
        self.jid = self.msg.computeJid

    def destroy(self):
        self._terminating = True
        if '_in_file' in self:
            pkio.unchecked_remove(self.pkdel('_in_file'))
        self._process.kill()
        try:
            self.cmds.remove(cmd)
        except Exception:
            pass

    def job_cmd_cmd(self):
        return ('sirepo', 'job_cmd', self._in_file)

    def job_cmd_cmd_stdin_env(self):
        return job.agent_cmd_stdin_env(
            cmd=self.job_cmd_cmd(),
            env=self.job_cmd_env(),
            pyenv=self.job_cmd_pyenv(),
            source_bashrc=self.job_cmd_source_bashrc(),
        )

    def job_cmd_env(self, env=None):
        pkdp('cccccccccccccccccccccccccccccccc')
        pkdp(self.msg.get('libFileUri', ''))
        pkdp('cccccccccccccccccccccccccccccccc')
        return job.agent_env(
            env=(env or PKDict()).pksetdefault(
                SIREPO_MPI_CORES=self.msg.mpiCores,
                SIREPO_SIM_DATA_LIB_FILE_URI=self.msg.get('libFileUri', ''),
            ),
        )

    def job_cmd_pyenv(self):
        return 'py2'

    def job_cmd_source_bashrc(self):
        return 'source $HOME/.bashrc'

    async def on_stdout_read(self, text):
        if self._terminating or not self.msg.opId:
            return
        try:
            await self.dispatcher.send(
                self.dispatcher.format_op(
                    self.msg,
                    job.OP_RUN if self._is_compute else job.OP_ANALYSIS,
                    reply=pkjson.load_any(text),
                )
            )
        except Exception as exc:
            pkdlog('text={} error={} stack={}', text, exc, pkdexc())

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

    async def _await_exit(self):
        try:
            await self._process.exit_ready()
            if self._terminating:
                return
            e = self._process.stderr.text.decode('utf-8', errors='ignore')
            if e:
                pkdlog('jid={} exit={} stderr={}', self.jid, self._process.returncode, e)
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
            pkdlog(
                'jid={} error={} returncode={} stack={}',
                self.jid,
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
                        error='job_agent error',
                    ),
                ),
            )
        finally:
            self.destroy()

    def _create_in_file(self):
        f = self.run_dir.join(
            _IN_FILE.format(job.unique_key()),
        )
        pkjson.dump_pretty(self.msg, filename=f, pretty=False)
        return f


class _SbatchCmd(_Cmd):

    def job_cmd_source_bashrc(self):
        if not self.msg.get('shifterImage'):
            return super().job_cmd_source_bashrc()
        return f'''
ulimit -c 0
unset PYTHONPATH
unset PYTHONSTARTUP
export PYENV_ROOT=/home/vagrant/.pyenv
export HOME=/home/vagrant
source /home/vagrant/.bashrc
eval export HOME=~$USER
{self._job_cmd_source_bashrc_dev()}
'''

    def job_cmd_cmd_stdin_env(self, *args, **kwargs):
        c, s, e = super().job_cmd_cmd_stdin_env()
        if self.msg.get('shifterImage'):
            c = ('shifter', f'--image={self.msg.shifterImage}', '/bin/bash', '--norc', '--noprofile', '-l')
        return c, s, e

    async def exited(self):
        await self._process.exit_ready()

    def _job_cmd_source_bashrc_dev(self):
        if not pkconfig.channel_in('dev'):
            return ''
        return 'export PYTHONPATH=$HOME/src/radiasoft/sirepo:$HOME/src/radiasoft/pykern'


class _SbatchRun(_SbatchCmd):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pkupdate(
            _start_time=0,
            _sbatch_id=None,
            _status_cb=None,
            _status='PENDING',
            _stopped_sentinel=self.run_dir.join('sbatch_status_stop'),
        )
        self.msg.jobCmd = 'sbatch_status'
        self.pkdel('_in_file').remove()

    def destroy(self):
        if self._status_cb:
            self._status_cb.stop()
            self._status_cb = None
        self._start_ready.set()
        if self._sbatch_id:
            i = self._sbatch_id
            self._sbatch_id = None
            p = subprocess.run(
                ('scancel', '--full', '--quiet', i),
                close_fds=True,
                cwd=str(self.run_dir),
                capture_output=True,
                text=True,
            )
            if p.returncode != 0:
                pkdlog(
                    'cancel error exit={} sbatch={} stderr={} stdout={}',
                    p.returncode,
                    i,
                    p.stderr,
                    p.stdout,
                )
        super().destroy()

    async def start(self):
        await self._prepare_simulation()
        if self._terminating:
            return
        p = subprocess.run(
            ('sbatch', self._sbatch_script()),
            close_fds=True,
            cwd=str(self.run_dir),
            capture_output=True,
            text=True,
        )
        m = re.search(r'Submitted batch job (\d+)', p.stdout)
#TODO(robnagler) if the guy is out of hours, will fail
        if not m:
            raise ValueError(
                f'Unable to submit exit={p.returncode} stdout={p.stdout} stderr={p.stderr}')
        self._sbatch_id = m.group(1)
        self.msg.pkupdate(
            sbatchId=self._sbatch_id,
            stopSentinel=str(self._stopped_sentinel),
        )
        self._status_cb = tornado.ioloop.PeriodicCallback(
            self._sbatch_status,
            self.msg.nextRequestSeconds * 1000,
        )
        self._start_ready = tornado.locks.Event()
        self._status_cb.start()
        await self._start_ready.wait()
        if self._terminating:
            return
        self._in_file = self._create_in_file()
        pkdlog(
            'opId={} sbatchId={} starting jobCmd={}',
            self.msg.opId,
            self._sbatch_id,
            self.msg.jobCmd,
        )
        await super().start()

    async def _prepare_simulation(self):
        c = _SbatchCmd(
            dispatcher=self.dispatcher,
            msg=self.msg.copy().pkupdate(
                jobCmd='prepare_simulation',
                # needed so replies not sent back to supervisor
                opId=None,
                # sequential job
                opName=job.OP_ANALYSIS,
            ),
        )
        await c.start()
        await c._await_exit()

    def _sbatch_script(self):
        i = self.msg.shifterImage
        s = o = ''
        if i:
#TODO(robnagler) provide via sbatch driver
            o = f'''#SBATCH --image={i}
#SBATCH --constraint=haswell
#SBATCH --qos=debug
#SBATCH --tasks-per-node=32'''
            s = '--cpu-bind=cores shifter'
        f = self.run_dir.join(self.jid + '.sbatch')
        f.write(f'''#!/bin/bash
#SBATCH --error={template_common.RUN_LOG}
#SBATCH --ntasks={self.msg.sbatchCores}
#SBATCH --output={template_common.RUN_LOG}
#SBATCH --time={self._sbatch_time()}
{o}
cat > bash.stdin <<'EOF'
{self.job_cmd_source_bashrc()}
{self.job_cmd_env()}
pyenv shell {self.job_cmd_pyenv()}
if [[ ! $LD_LIBRARY_PATH =~ /usr/lib64/mpich/lib ]]; then
    export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/usr/lib64/mpich/lib
fi
#TODO(robnagler) need to get command from prepare_simulation
exec python {template_common.PARAMETERS_PYTHON_FILE}
EOF
exec srun {s} /bin/bash bash.stdin
'''
        )
        return f

    async def _sbatch_status(self):
        if self._terminating:
            return
        p = subprocess.run(
            ('scontrol', 'show', 'job', self.msg.sbatchId),
            cwd=str(self.run_dir),
            close_fds=True,
            capture_output=True,
            text=True,
        )
        if p.returncode != 0:
            pkdlog(
                'scontrol error exit={} sbatch={} stderr={} stdout={}',
                p.returncode,
                self._sbatch_id,
                p.stderr,
                p.stdout,
            )
            return
        r = re.search(r'(?<=JobState=)(\S+)(?= Reason)', p.stdout)
        if not r:
            pkdlog(
                'opId={} failed to find JobState in sderr={} stdout={}',
                self.msg.opId,
                p.stderr,
                p.stdout,
            )
            return
        self._status = r.group()
        if self._status == 'PENDING':
            return
        else:
            if not self._start_ready.is_set():
                self._start_time = int(time.time())
                self._start_ready.set()
            if self._status in ('COMPLETING', 'RUNNING'):
                return
        c = self._status == 'COMPLETED'
        self._stopped_sentinel.write(job.COMPLETED if c else job.ERROR)
        if not c:
            # because have to await before calling destroy
            self._terminating = True
            pkdlog(
                'sbatch={} unexpected state={}',
                self._sbatch_id,
                self._status,
            )
            await self.dispatcher.send(
                self.dispatcher.format_op(
                    self.msg,
                    job.OP_ERROR,
                    reply=PKDict(
                        state=job.ERROR,
                        error=f'sbatch status={self._status}'
                    ),
                )
            )
            self.destroy()

    def _sbatch_time(self):
        return str(datetime.timedelta(
            seconds=int(
                datetime.timedelta(hours=float(self.msg.sbatchHours)).total_seconds(),
            ),
        ))


class _Process(PKDict):
    def __init__(self, cmd):
        super().__init__()
        self.update(
            stderr=None,
            stdout=None,
            cmd=cmd,
            _exit=tornado.locks.Event(),
        )

    async def exit_ready(self):
        await self._exit.wait()
        await self.stdout.stream_closed.wait()
        await self.stderr.stream_closed.wait()

    def kill(self):
        # TODO(e-carlin): Terminate?
        if 'returncode' in self or '_subprocess' not in self:
            return
        p = None
        try:
            p = self.pkdel('_subprocess').proc.pid
            os.killpg(p, signal.SIGKILL)
        except ProcessLookupError as e:
            pass
        except Exception as e:
            pkdlog('kill pid={} exception={}', p, e)

    def start(self):
        # SECURITY: msg must not contain agentId
        assert not self.cmd.msg.get('agentId')
        c, s, e = self.cmd.job_cmd_cmd_stdin_env()
        pkdlog('cmd={} stdin={}', c, s.read())
        s.seek(0)
        self._subprocess = tornado.process.Subprocess(
            c,
            close_fds=True,
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


class _ReadJsonlStream(_Stream):
    def __init__(self, stream, cmd):
        self.proceed_with_read = tornado.locks.Condition()
        self.read_occurred = tornado.locks.Condition()
        self.cmd = cmd
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
