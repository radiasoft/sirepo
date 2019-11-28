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
        # TODO(e-carlin): use _JobProcess in docker and local
        p = _JobProcess(msg=msg, comm=self)
        # TODO(e-carlin): Use _DockerJobProcess and _SBatchProcess only on NERSC
        # p = _DockerJobProcess(msg=msg, comm=self)
        # if msg.isParallel:
        #     p = _SBatchProcess(msg=msg, comm=self)
#TODO(robnagler) there should only be one computeJid per agent.
#   background_percent_complete is not an analysis
        assert msg.computeJid not in self.processes
        self.processes[msg.computeJid] = p
        p.start()


def _docker_get_container_name(msg):
    return '{}_{}'.format(msg.computeJid, msg.jobProcessCmd)


def _docker_rm_cmd(name):
    return (
        'docker',
        'rm',
        '-f',
        name,
    )


def _docker_run_cmd_base(msg, name):
    return (
        'docker',
        'run',
        '--rm',
        '--name={}'.format(name),
        '--interactive',
#TODO(robnagler) propagated via stdin
        '--env=PYTHONUNBUFFERED=1',
        '--env=SIREPO_SRDB_ROOT={}'.format(msg.agentDbRoot),
        '--env=SIREPO_AUTH_LOGGED_IN_USER={}'.format(msg.uid),
        '--volume=/home/vagrant/src/radiasoft/sirepo/sirepo:/home/vagrant/.pyenv/versions/2.7.16/envs/py2/lib/python2.7/site-packages/sirepo',
        '--volume=/home/vagrant/src/radiasoft/pykern/pykern:/home/vagrant/.pyenv/versions/2.7.16/envs/py2/lib/python2.7/site-packages/pykern',
#TODO(robnagler) need to figure out temp_dir for lib_files
        '--volume={}:{}'.format(msg.runDir, msg.runDir),
        '--workdir={}'.format(msg.runDir),
        'radiasoft/sirepo:dev',
        '/bin/bash',
        '-l',
        '-c',
    )


class _JobProcess(PKDict):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._in_file = self._create_in_file()
        self._subprocess = _Subprocess(
                self.subprocess_cmd_stdin_env,
                self._on_stdout_read,
                msg=self.msg,
            )
        self._terminating = False

    def kill(self):
        self._terminating = True
        self._subprocess.kill()

    def start(self):
        self._subprocess.start()
        tornado.ioloop.IOLoop.current().add_callback(
            self._on_exit
        )

    def subprocess_cmd_stdin_env(self):
        return job.subprocess_cmd_stdin_env(
            ('sirepo', 'job_process', self._in_file),
            PKDict(
                PYTHONUNBUFFERED='1',
                SIREPO_AUTH_LOGGED_IN_USER=sirepo.auth.logged_in_user(),
                SIREPO_MPI_CORES=self.msg.mpiCores,
                SIREPO_SIM_LIB_FILE_URI=self.msg.get('libFileUri', ''),
                SIREPO_SRDB_ROOT=sirepo.srdb.root(),
            ),
            pyenv='py2',
        )

    def _create_in_file(self):
        f = self.msg.runDir.join(
            _IN_FILE.format(job.unique_key()),
        )
        pkio.mkdir_parent_only(f)
        pkjson.dump_pretty(self.msg, filename=f, pretty=False)
        return f

    async def _on_exit(self):
        try:
            await self._subprocess.exit_ready()
            if self._in_file:
                pkio.unchecked_remove(self._in_file)
                self._in_file = None
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


class _DockerJobProcess(_JobProcess):

    def subprocess_cmd_stdin_env(self):
        # The volumes mounted and no cascading of env is problematic for docker. Docker is
        # is going to be replaced with singulatiry which doesn't have these problems so
        # it is fine for now
        self._in_file = self._create_in_file()
        self._container_name = _docker_get_container_name(self.msg)
        return job.subprocess_cmd_stdin_env(
#TODO(robnagler) have job.subprocess_cmd_stdin_env aggregate stdin
            _docker_run_cmd_base(self.msg, self._container_name) + ('sirepo job_process {}'.format(self._in_file),),
            PKDict()
        )

    def kill(self):
        self._terminating = True
        subprocess.check_call(_docker_rm_cmd(self._container_name))

    async def exited(self):
        await self._subprocess.exit_ready()


class _GetSbatchParallelStatusDockerJobProcess(_DockerJobProcess):

    async def _on_exit(self):
        await self._subprocess.exit_ready()
        if self._terminating:
            e = self._subprocess.stderr.text.decode('utf-8', errors='ignore')
            if e:
                pkdlog('error={}', e)
            return
        else:
            # TODO(e-carlin): We should restart the job if this happens
            pkdlog(
                'error: exited without a termination request'
            )


class _SBatchProcess(PKDict):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.update(
            _parallel_status_process=None,
            _completed_parallel_status_process=None,
            _sbatch_job_id=None,
        )

        self.msg.update(
            # TODO(e-carlin): job_process.do_compute() has the same code
            isRunning=False,
            simulationStatus=PKDict(
                computeJobStart=None,
                state=job.PENDING,
            ),
        )

    def kill(self):
        if self._parallel_status_process is not None:
            self._parallel_status_process.kill()
        if self._completed_parallel_status_process is not None:
            self._completed_parallel_status_process.kill()
        if self._sbatch_job_id is not None:
            subprocess.check_call(
                # TODO(e-carlin): what signal do we want to send?
                # currently this defaults to SIGKILL
                ('scancel', '--full', '--quiet', self._sbatch_job_id)
            )

    def start(self):
        tornado.ioloop.IOLoop.current().add_callback(
            self._start_compute
        )

    async def _await_job_completion_and_parallel_status(self, job_id):
        parallel_status_running = False
        while True:
            s = self._get_job_sbatch_state(job_id)
            assert s in ('running', 'pending', 'completed', 'completing'), \
                'invalid state={}'.format(s)
            if s in ('running', 'completed', 'completing'):
                if not parallel_status_running:
                    self._begin_get_parallel_status()
                    parallel_status_running = True
            if s == 'completed':
                break
            await tornado.gen.sleep(2) # TODO(e-carlin): longer poll
        self._kill_parallel_status_process()
        await self._get_completed_parallel_status()

    def _begin_get_parallel_status(self):
        self._compute_job_start_time = int(time.time())
        m = self.msg.copy().update(
            isRunning=True,
            jobProcessCmd='get_sbatch_parallel_status',
            simulationStatus=PKDict(
                computeJobStart=self._compute_job_start_time,
                state=job.RUNNING,
            ),
        )
        self._parallel_status_process = _GetSbatchParallelStatusDockerJobProcess(
            msg=m,
            comm=self.comm,
        )
        self._parallel_status_process.start()

    async def _get_completed_parallel_status(self):
        m = self.msg.copy().update(
            isRunning=False,
            jobProcessCmd='get_sbatch_parallel_status_once',
            simulationStatus=PKDict(
                computeJobStart=self._compute_job_start_time,
                state=job.COMPLETED,
            ),
        )
        # POSIT: This is the only subprocess in DockerJobProcess that removes
        # our jid from self.comm.processes
        self._completed_parallel_status_process = p = _DockerJobProcess(
            msg=m,
            comm=self.comm,
        )
        p.start()
        await p.exited()

    def _get_job_sbatch_state(self, job_id):
        o = subprocess.check_output(
            ('scontrol', 'show', 'job', job_id)
        ).decode('utf-8')
        r = re.search(r'(?<=JobState=)(.*)(?= Reason)', o) # TODO(e-carlin): Make middle [A-Z]+
        assert r, 'output={}'.format(s)
        return r.group().lower()

    def _get_sbatch_script(self, cmd):
        # TODO(e-carlin): configure the SBATCH* parameters
        self._container_name = _docker_get_container_name(self.msg)
        return'''#!/bin/bash
#SBATCH --partition=compute
#SBATCH --ntasks=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=4
#SBATCH --mem-per-cpu=128M
#SBATCH -e {}
#SBATCH -o {}
{}
'''.format(
            template_common.RUN_LOG,
            template_common.RUN_LOG,
            ' '.join(_docker_run_cmd_base(self.msg, self._container_name) + ('"' + ' '.join(cmd) + '"',)),
        )

    def _kill_parallel_status_process(self):
        self._parallel_status_process.kill()
        self._parallel_status_process = None

    def _prepare_simulation(self):
        c, s, _ = _DockerJobProcess(
            msg=self.msg.copy().update(jobProcessCmd='prepare_simulation'),
        ).subprocess_cmd_stdin_env()
        r = subprocess.check_output(c, stdin=s)
        return pkjson.load_any(r).cmd

    async def _send_op_error(self, reply):
        # POSIT: jobProcessCmd is the only field every changed in msg
        await self.comm.send(
            self.comm.format_op(
                self.msg,
                job.OP_ERROR,
                reply=reply,
            )
        )

    async def _start_compute(self):
        try:
            self._sbatch_job_id =  self._submit_compute_to_sbatch(
                self._prepare_simulation(),
            )
            await self._await_job_completion_and_parallel_status(
                self._sbatch_job_id,
            )
        except Exception as e:
            await self._send_op_error(
                PKDict(
                    state=job.ERROR,
                    error=str(e),
                    stack=pkdexc(),
                    opDone=True,
                )
            )
        finally:
            self.comm.processes.pkdel(self.msg.computeJid)

    def _submit_compute_to_sbatch(self, cmd):
        s = self._get_sbatch_script(cmd)
        n = str(self.msg.runDir.join('sbatch.job'))
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
            subprocess_cmd_stdin_env=subprocess_cmd_stdin_env,
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
        cmd, stdin, env = self.subprocess_cmd_stdin_env()
        self._subprocess = tornado.process.Subprocess(
            cmd,
            cwd=str(self.msg.runDir),
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
