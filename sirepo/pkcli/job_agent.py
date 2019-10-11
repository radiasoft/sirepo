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
from sirepo import job_agent_process, job, mpi
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
import tornado.queues
import tornado.websocket


#: Long enough for job_process to write result in run_dir
_TERMINATE_SECS = 3

_RETRY_SECS = 1

_IN_FILE = 'in-{}.json'

_STATUS_FILE = 'job_agent.json'

_STATUS_FILE_COMMON = PKDict(version=1)

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
        supervisor_uri=pkconfig.Required(str, 'how to connect to the supervisor'),
    )
    pkdlog('{}', cfg)
    i = tornado.ioloop.IOLoop.current()
    c = _Comm()
    s = lambda n, x: i.add_callback_from_signal(c.kill)
    signal.signal(signal.SIGTERM, s)
    signal.signal(signal.SIGINT, s)
    i.spawn_callback(c.loop)
    i.start()


def _subprocess_env():
    env = PKDict(os.environ)
    pkcollections.unchecked_del(
        env,
        *(k for k in env if _EXEC_ENV_REMOVE.search(k)),
    )
    env.SIREPO_MPI_CORES = str(mpi.cfg.cores)
    return env


class _Process(PKDict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._in_file = None
        self._subprocess = None
        self._terminating = False
        self.compute_status_file = None
        self.compute_status = None

    async def start(self):
        f = self._in_file = self.run_dir.join(_IN_FILE.format(job.unique_key()))
        # SECURITY msg must not contain agent_id
        assert not self.msg.get('agent_id')
        pkjson.dump_pretty(self.msg, filename=f, pretty=False)
        env = _subprocess_env()
        if self.msg.job_process_cmd == 'compute':
            #TODO(robnagler) background_percent_complete needs to start if parallel
            self.compute_status_file = self.run_dir.join(_STATUS_FILE)
            self.compute_status = PKDict(_STATUS_FILE_COMMON).update(
                compute_hash=self.msg.compute_hash,
                start_time=time.time(),
                status=job.Status.RUNNING.value,
            )
            #TODO(robnagler) pkio.atomic_write?
            self.compute_status_file.write(self.compute_status)
        # we're in py3 mode, and regular subprocesses will inherit our
        # environment, so we have to manually switch back to py2 mode.
        env['PYENV_VERSION'] = 'py2'
        p = self._subprocess = tornado.process.Subprocess(
            ('pyenv', 'exec', 'sirepo', 'job_process', str(f)),
            # SECURITY: need to change cwd, because agent_dir has agent_id
            cwd=self.run_dir,
            start_new_session=True,
            stdin=subprocess.DEVNULL,
            stdout=tornado.process.Subprocess.STREAM,
            stderr=tornado.process.Subprocess.STREAM,
            env=env,
        )
        p.set_exit_callback(self._exit)

        async def collect(stream, out):
            out.append(await stream.read_until_close())

        i = tornado.ioloop.IOLoop.current()
        self.stdout = bytearray()
        self.stderr = bytearray()
        i.spawn_callback(collect, p.stdout, self.stdout)
        i.spawn_callback(collect, p.stderr, self.stderr)

    async def cancel(self, run_dir):
        if not self._terminating:
            # Will resolve itself, b/c harmless to call proc.kill
            tornado.ioloop.IOLoop.current().call_later(
                _TERMINATE_SECS,
                self._kill,
            )
            self._terminating = True
            self._done(job.Status.CANCELED.value)
            self._subprocess.proc.terminate()

    def kill(self):
        self._terminating = True
        if self._subprocess:
            self._done(job.Status.CANCELED.value)
            self._subprocess.proc.kill()
            self._subprocess = None

    def _done(self, status):
        if self.compute_status_file:
            self.compute_status.status = status
            self.compute_status_file.write(self.compute_status)
            self.compute_status_file = None
        if self._in_file:
            pkio.unchecked_remove(self._in_file)
            self._in_file = None

    async def _compute_status(self, out):
        try:
             if out:
                 await self.comm.write_message(
                     self.msg,
                     job.OP_OK,
                     runner_status=pkjson.load_any(out),
                 )
                 return
        except Exception as e:
            pkdlog('error={} msg={}', e, self.msg)
            await self.comm.write_message(self.msg, job.OP_OK, compute_status=None)

    async def _exit(self, return_code):
        if self._terminating:
            return
        self._done(job.Status.COMPLETED.value if return_code == 0 else job.Status.ERROR.value)
        e = self.stderr.decode('utf-8', errors='ignore')
        o = self.stdout.decode('utf-8', errors='ignore')
        if self.msg.job_process_cmd == 'compute_status':
            await self._compute_status(o)
        elif self.msg.job_process_cmd == 'compute':
            await self.comm.write_message(
                self.msg,
                job.OP_COMPUTE_STATUS,
                compute_status=self.compute_status,
            )
        else:
            # must be analysis of some sort, even background_percent_complete
            try:
                if o:
                    await self.comm.write_message(
                        self.msg,
                        job.OP_ANALYSIS,
                        output=o,
                    )
            except Exception:
                pkdlog('error={} msg={}', e, self.msg)
            await self.comm.write_message(self.msg, job.OP_ERROR, error=e, output=o)


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
                    #TODO(robnagler) connect_timeout, max_message_size, ping_interval, ping_timeout
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
                            await c.write_message(m)
                    except tornado.websocket.WebSocketClosedError as e:
                        pkdlog('error={}', e)
                        break
                    m = await c.read_message()
                    pkdc('msg={}', job.LogFormatter(m))
                    if m is None:
                        break
                    m = await self._op(m)
            except Exception as e:
                pkdlog('error={} \n{}', e , pkdexc())

    async def write_message(self, msg, op, **kwargs):
        try:
            await self._websocket.write_message(self._format_reply(msg, op, **kwargs))
        except Exception as e:
            pkdlog('error={}', e)

    def _format_reply(self, msg, op, **kwargs):
        if msg:
            # TODO(e-carlin): remove agent_id
            kwargs['op_id'] = msg.get('op_id')
            kwargs['jid'] = msg.get('jid')
        return pkjson.dump_bytes(
            PKDict(agent_id=cfg.agent_id, **kwargs),
        )

    async def _op(self, msg):
        try:
            m = pkjson.load_any(msg)
            m.run_dir = pkio.py_path(m.run_dir)
            r = await getattr(self, '_op_' + m.op)(m)
            if r:
                r =  r if isinstance(r, bytes) else self._format_reply(m, job.OP_OK)
                return r
            return None
        except Exception as e:
            err = 'exception=' + str(e)
            stack = pkdexc()
            return self._format_reply(None, job.OP_ERROR, error=err, stack=stack)

    async def _op_cancel(self, msg):
        p = self._processes.get(msg.jid)
        if not p:
            return self._format_reply(msg, job.OP_ERROR, error='no such jid')
        await p.cancel()
        return True

    async def _op_kill(self, msg):
        self.kill()
        return True

    async def _op_run(self, msg):
        m = msg.copy()
        del m['op_id ']
        await self._process(m)
        return True

    async def _op_compute_status(self, msg):
        try:
            p = self._processes.get(msg.jid)
            return self._format_reply(
                msg,
                job.OP_OK,
                compute_status=p and p.compute_status \
                or pkjson.load_any(msg.run_dir.join(_STATUS_FILE)),
            )
        except Exception:
            f = msg.run_dir.join(job.RUNNER_STATUS_FILE)
            if f.exists():
                assert msg.jid not in self._processes
                msg.update(
                    job_process_cmd='compute_status',
                )
                await self._process(msg)
                return
        return self._format_reply(msg, job.OP_OK, compute_status=job.Status.MISSING.value)

    async def _process(self, msg):
        p = _Process(msg=msg, comm=self)
        assert msg.jid not in self._processes
        self._processes[msg.jid] = p
        await p.start()
