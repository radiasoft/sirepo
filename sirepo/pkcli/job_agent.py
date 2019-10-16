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

_STATUS_FILE = 'job-agent.json'

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
        self.compute_status = None
        self.compute_status_file = None
        self.jid = self.msg.jid
        self._in_file = None
        self._subprocess = None
        self._terminating = False

    def start(self):
        # SECURITY: msg must not contain agent_id
        assert not self.msg.get('agent_id')
        if self.msg.job_process_cmd == 'compute':
            #TODO(robnagler) background_percent_complete needs to start if parallel
            self._write_comput_status_file(job.Status.RUNNING.value)
        # TODO(e-carlin): remove await
        self._start_job_process()

    def _write_comput_status_file(self, status):
        self.compute_status_file = self.msg.run_dir.join(_STATUS_FILE)
        pkio.mkdir_parent_only(self.compute_status_file)
        self.compute_status = PKDict(_STATUS_FILE_COMMON).update(
            compute_hash=self.msg.compute_hash,
            start_time=time.time(),
            status=status,
        )
        #TODO(robnagler) pkio.atomic_write?
        self.compute_status_file.write(self.compute_status)

    def _start_job_process(self):
        env = _subprocess_env()
        env['PYENV_VERSION'] = 'py2'
        self._in_file = self.msg.run_dir.join(_IN_FILE.format(job.unique_key()))
        self.msg.run_dir = str(self.msg.run_dir) # TODO(e-carlin): Find a better solution for serial and deserialization
        pkjson.dump_pretty(self.msg, filename=self._in_file, pretty=False)
        self._subprocess = tornado.process.Subprocess(
            ('pyenv', 'exec', 'sirepo', 'job_process', str(self._in_file)),
            # SECURITY: need to change cwd, because agent_dir has agent_id
            cwd=self.msg.run_dir,
            start_new_session=True,
            stdin=subprocess.DEVNULL,
            stdout=tornado.process.Subprocess.STREAM,
            stderr=tornado.process.Subprocess.STREAM,
            env=env,
        )
        async def collect(stream, out):
            out.extend(await stream.read_until_close())
        i = tornado.ioloop.IOLoop.current()
        self.stdout = bytearray()
        self.stderr = bytearray()
        i.spawn_callback(collect, self._subprocess.stdout, self.stdout)
        i.spawn_callback(collect, self._subprocess.stderr, self.stderr)
        # self._subprocess.set_exit_callback(self.exit) # TODO(e-carlin): delete
        self._subprocess.set_exit_callback(self._exit)

    def _load_output(self):
        e = None
        o = None
        try:
            e = pkjson.load_any(self.stderr)
        except json.JSONDecodeError:
            s = self.stderr.decode('utf-8')
            if s:
                e = PKDict(error=s) # TODO(e-carlin): errors='ignore' ?
        except Exception as exc:
            e = PKDict(error=exc)
        if e:
            try:
                o = pkjson.load_any(self.stdout)
            except json.JSONDecodeError:
                pass
            return o, e
        o = pkjson.load_any(self.stdout)
        return o, e

    def _exit(self, return_code):
        # TODO(e-carlin): this is ugly. fix error handling. i think elimnate the nested do() func
        async def do():
            try:
                self.comm.remove_process(self.jid)
                if self._terminating:
                    return
                o, e = self._load_output()
                error = e or return_code != 0
                self._done(job.Status.ERROR.value if error else job.Status.COMPLETED.value)
                if error:
                    await self.comm.write_message(
                        self.msg,
                        job.OP_ERROR,
                        error=e,
                        output=o,
                        compute_status=job.Status.ERROR.value,
                    )
                elif self.msg.job_process_cmd == 'compute':
                    await self.comm.write_message(
                        self.msg,
                        job.OP_OK,
                        output=o,
                        compute_status=job.Status.COMPLETED.value,
                    )
                elif self.msg.job_process_cmd == 'compute_status':
                    await self.comm.write_message(
                        self.msg,
                        job.OP_COMPUTE_STATUS,
                        **o
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
        tornado.ioloop.IOLoop.current().spawn_callback(do)
            

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
            PKDict(agent_id=cfg.agent_id, op=op, **kwargs),
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
        await p.cancel() # TODO(e-carlin): cancel should be sync fire and forget
        return True

    async def _op_kill(self, msg):
        self.kill()
        return True

    async def _op_result(self, msg):
        msg.update(job_process_cmd='result')
        self._process(msg)
        return False

    async def _op_run(self, msg):
        m = msg.copy()
        del m['op_id']
        m.update(job_process_cmd='compute')
        self._process(m)
        return self._format_reply(
            msg,
            job.OP_OK,
            compute_status=job.Status.RUNNING.value,
        )

    async def _op_compute_status(self, msg):
        try:
            p = self._processes.get(msg.jid)
            return self._format_reply(
                msg,
                job.OP_COMPUTE_STATUS,
                compute_status=p and p.compute_status \
                or pkjson.load_any(msg.run_dir.join(_STATUS_FILE)),
            )
        except Exception:
            f = msg.run_dir.join(job.RUNNER_STATUS_FILE)
            if f.check():
                assert msg.jid not in self._processes
                msg.update(job_process_cmd='compute_status')
                self._process(msg)
                return False
        return self._format_reply(
            msg,
            job.OP_COMPUTE_STATUS,
            compute_status=job.Status.MISSING.value,
        )

    def _process(self, msg):
        p = _Process(msg=msg, comm=self)
        assert msg.jid not in self._processes
        self._processes[msg.jid] = p
        p.start()
    
    def remove_process(self, jid):
        assert jid in self._processes
        del self._processes[jid]
