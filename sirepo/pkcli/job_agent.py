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


#: Long enough for job_cmd to write result in run_dir
_TERMINATE_SECS = 3

_RETRY_SECS = 1

_IN_FILE = 'in-{}.json'

_PID_FILE = 'job_agent.pid'

cfg = None


def start():
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
    def s(*args):
        return i.add_callback_from_signal(_terminate, d)
    signal.signal(signal.SIGTERM, s)
    signal.signal(signal.SIGINT, s)
    i.spawn_callback(d.loop)
    i.start()


def start_sbatch():
    def get_host():
        h = socket.gethostname()
        if '.' not in h:
            h = socket.getfqdn()
        return h

    def kill_agent(pid_file):
        if get_host() == pid_file.host:
            os.kill(pid_file.pid, signal.SIGKILL)
        else:
            try:
                subprocess.run(
                    ('ssh', pid_file.host, 'kill', '-KILL', str(pid_file.pid)),
                    capture_output=True,
                    text=True,
                ).check_returncode()
            except subprocess.CalledProcessError as e:
                if '({}) - No such process'.format(pid_file.pid) not in e.stderr:
                    pkdlog(
                        'cmd={cmd} returncode={returncode} stderr={stderr}',
                        **vars(e)
                    )
    f = None
    try:
        f = pkjson.load_any(pkio.py_path(_PID_FILE))
    except Exception as e:
        if not pkio.exception_is_not_found(e):
            pkdlog('error={} stack={}', e, pkdexc())
    try:
        if f:
            kill_agent(f)
    except Exception as e:
        pkdlog('error={} stack={}', e, pkdexc())
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
#TODO(robnagler) https://github.com/radiasoft/sirepo/issues/2195
        pkio.unchecked_remove(_PID_FILE)


class _Dispatcher(PKDict):

    def __init__(self):
        super().__init__(cmds=[], _fastcgi_cmd=None)

    def format_op(self, msg, opName, **kwargs):
        if msg:
            kwargs['opId'] = msg.get('opId')
        return pkjson.dump_bytes(
            PKDict(agentId=cfg.agent_id, opName=opName).pksetdefault(**kwargs),
        )

    async def job_cmd_reply(self, msg, op_name, text):
        try:
            r = pkjson.load_any(text)
        except Exception as e:
            op_name = job.OP_ERROR
            r = PKDict(
                state=job.ERROR,
                error=f'unable to parse job_cmd output',
                stdout=text,
            )
        try:
            await self.send(self.format_op(msg, op_name, reply=r))
        except Exception as e:
            pkdlog('reply={} error={} stack={}', r, e, pkdexc())
            # something is really wrong, because format_op is messed up
            raise

    async def loop(self):
        while True:
            self._websocket = None
            try:
#TODO(robnagler) connect_timeout, max_message_size, ping_interval, ping_timeout
                self._websocket = await tornado.websocket.websocket_connect(
                    tornado.httpclient.HTTPRequest(
                        url=cfg.supervisor_uri,
                        validate_cert=sirepo.job.cfg.verify_tls,
                    ),
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
            pkdlog('op={} opId={} runDir={}', m.opName, m.get('opId'), m.get('runDir'))
            pkdc('m={}', m)
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

    async def _op_sbatch_login(self, msg):
        await self.send(
            self.format_op(msg, job.OP_OK, reply=PKDict(loginSuccess=True)),
        )

    async def _cmd(self, msg):
        if msg.opName == job.OP_ANALYSIS and msg.jobCmd != 'fastcgi':
            return await self._fastcgi_op(msg)
        c = _Cmd
        if msg.jobRunMode == job.SBATCH:
            c = _SbatchRun if msg.isParallel else _SbatchCmd
        p = c(msg=msg, dispatcher=self)
        if msg.jobCmd == 'fastcgi':
            self._fastcgi_cmd = p
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
                            error='internal error',
                        ),
                    )
                )
            except Exception as e:
                pkdlog('msg={} error={} stack={}', msg, e, pkdexc())

        pkdlog('msg={} error={} stack={}', msg, error, stack)
        # destroy _fastcgi state first, then send replies to avoid
        # asynchronous modification of _fastcgi state.
        self._fastcgi_remove_handler()
        q = self._fastcgi_msg_q
        self._fastcgi_msg_q = None
        self._fastcgi_cmd.destroy()
        self._fastcgi_cmd = None
        if msg:
            await _reply_error(msg)
        while q.qsize() > 0:
            await _reply_error(q.get_nowait())
            q.task_done()


    async def _fastcgi_op(self, msg):
        if not self._fastcgi_cmd:
            m = msg.copy()
            m.jobCmd = 'fastcgi'
            m.opId = None
            self._fastcgi_file = 'job_cmd_fastcgi.sock'
            self._fastcgi_msg_q = tornado.queues.Queue(1)
            pkio.unchecked_remove(self._fastcgi_file)
            # Avoid OSError: AF_UNIX path too long (max=100)
            # Use relative path
            m.fastcgiFile = self._fastcgi_file
            # Runs in a agent's directory, but chdir's to real runDirs
            m.runDir = pkio.py_path()
            # Kind of backwards, but it makes sense since we need to listen
            # so _do_fastcgi can connect
            self._fastcgi_remove_handler = tornado.netutil.add_accept_handler(
                tornado.netutil.bind_unix_socket(self._fastcgi_file),
                self._fastcgi_accept,
            )
            # last thing, because of await: start fastcgi process
            await self._cmd(m)
        self._fastcgi_msg_q.put_nowait(msg)
        return None

    async def _fastcgi_read(self, connection):
        s = None
        m = None
        try:
            s = tornado.iostream.IOStream(connection)
            while True:
                m = await self._fastcgi_msg_q.get()
                # Avoid issues with exceptions. We don't use q.join()
                # so not an issue to call before work is done.
                self._fastcgi_msg_q.task_done()
                await s.write(pkjson.dump_bytes(m) + b'\n')
                await self.job_cmd_reply(
                    m,
                    job.OP_ANALYSIS,
                    await s.read_until(b'\n', 1e8),
                )
        except Exception as e:
            await self._fastcgi_handle_error(m, e, pkdexc())
        finally:
            if s:
                s.close()


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
        return job.agent_env(
            env=(env or PKDict()).pksetdefault(
                SIREPO_MPI_CORES=self.msg.get('mpiCores', 1),
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
            await self.dispatcher.job_cmd_reply(
                self.msg,
                job.OP_RUN if self._is_compute else job.OP_ANALYSIS,
                text,
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

    async def exited(self):
        await self._process.exit_ready()

    def job_cmd_source_bashrc(self):
        if not self.msg.get('shifterImage'):
            return super().job_cmd_source_bashrc()
        return f'''
ulimit -c 0
unset PYTHONPATH
unset PYTHONSTARTUP
export PYENV_ROOT=/home/vagrant/.pyenv
export HOME=/home/vagrant
source /home/vagrant/.bashrc >& /dev/null
eval export HOME=~$USER
'''

    def job_cmd_cmd_stdin_env(self, *args, **kwargs):
        c, s, e = super().job_cmd_cmd_stdin_env()
        if self.msg.get('shifterImage'):
            c = ('shifter', f'--image={self.msg.shifterImage}', '/bin/bash', '--norc', '--noprofile', '-l')
        return c, s, e

    def job_cmd_env(self):
        e = PKDict()
        if pkconfig.channel_in('dev'):
            h = pkio.py_path('~/src/radiasoft')
            e.PYTHONPATH = '{}:{}'.format(h.join('sirepo'), h.join('pykern'))
        return super().job_cmd_env(e)


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
        q = "debug" if self.msg.sbatchHours < 0.5 \
            and self.msg.sbatchCores < 62 * 32 else "regular"
        if i:
#TODO(robnagler) provide via sbatch driver
            o = f'''#SBATCH --image={i}
#SBATCH --constraint=haswell
#SBATCH --qos={q}
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
            start_new_session=True,
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


def _terminate(dispatcher):
    dispatcher.terminate()
    pkio.unchecked_remove(_PID_FILE)
