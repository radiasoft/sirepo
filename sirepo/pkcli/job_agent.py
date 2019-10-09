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
from sirepo import job_agent_process
import sys
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

_AGENT_FILE = 'job_agent.json'

_AGENT_FILE_COMMON = PKDict(version=1)

cfg = None


def default_command():
    job.init()
    global cfg

    cfg = pkconfig.init(
        agent_id=pkconfig.Required(str, 'id of this agent'),
        supervisor_uri=pkconfig.Required(str, 'how to connect to the supervisor'),
    )
    pkdlog('{}', cfg)
    i = tornado.ioloop.IOLoop.current()
    m = _Main()
    s = lambda n, x: i.add_callback_from_signal(m.terminate)
    signal.signal(signal.SIGTERM, s)
    signal.signal(signal.SIGINT, s)
    i.spawn_callback(m.loop)
    i.start()


class _Process(PKDict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._agent_file = None
        self._in_file = None
        self._subprocess = None
        self._terminating = False

    async def start(self):
        f = self._in_file = self.run_dir.join(_IN_FILE.format(job.unique_key()))
        # SECURITY msg must not contain agent_id
        assert not self.msg.get('agent_id')
        pkjson.dump_pretty(self.msg, filename=f, pretty=False)
        env = _subprocess_env()
#TODO(robnagler) should this be here?
        if msg.job_process_cmd == 'compute':
            self._agent_file = self.run_dir.join(_AGENT_FILE)
            self._agent_file_data = PKDict(_AGENT_FILE_COMMON).update(
                compute_hash=self.msg.compute_hash,
                start_time=time.time(),
                status=job.Status.RUNNING.value,
            )
#TODO(robnagler) pkio.atomic_write?
        self._agent_file.write(self._agent_file_data)
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

        async def collect(stream, out_array):
            out_array += await stream.read_until_close()

        i = tornado.ioloop.IOLoop.current()
        self.stdout = bytearray()
        self.stderr = bytearray()
        i.spawn_callback(collect, p.stdout, self.stdout)
        i.spawn_callback(collect, p.stderr, self.stderr)

    def do_status(self, msg):
        """Get the current status of a specific job in the given run_dir."""
        j, s = self._run_dir_status(msg)
        return s if j == msg.jhash else job.Status.MISSING

    async def cancel(self, run_dir):
        if not self._terminating:
            # Will resolve itself, b/c harmless to call proc.kill
            tornado.ioloop.IOLoop.current().call_later(
                _TERMINATE_SECS,
                self._kill,
            )
            self._terminating = True
            self._commit(job.Status.CANCELED.value)
            self._subprocess.proc.terminate()

    def kill(self)
        self._terminating = True
        if self._subprocess:
            self._commit(job.Status.CANCELED.value)
            self._subprocess.proc.kill()
            self._subprocess = None

    def _commit(self, status):
        if self._agent_file:
            self._agent_file_data.status = status
            self._agent_file.write(self._agent_file_data)
            self._agent_file = None
        if self._in_file:
            pkio.unchecked_remove(self._in_file)
            self._in_file = None

    async def _exit(self, return_code):
        if self._terminating:
            return
        self._commit(job.Status.COMPLETED.value if return_code == 0 else job.Status.ERROR.value)
        self.stderr.decode('utf-8', errors='ignore')
        report done
        kill backgournd_percent timer
        write_result cannot exist;
        pass

    def _run_dir_status(self, msg):
        """Get the current status of whatever's happening in run_dir.

        Returns:
        Tuple of (jhash or None, status of that job)

        """
        i = msg.run_dir.join('in.json')
        s = msg.run_dir.join('status')
        if i.exists() and s.exists():
#TODO(robnagler) maybe we don't want this constraint?
            # status should be recorded on disk XOR in memory
            assert msg.run_dir not in self._compute_jobs
            j = pkjson.load_any(i).reportParametersHash
            x = None
            try:
                x = s.read()
                s = job.Status(x)
            except ValueError:
                pkdlog('unexpected status={} file={}', x, s)
                s = job.Status.ERROR
            return j, s
        elif msg.run_dir in self._compute_jobs:
            c = self._compute_jobs[msg.run_dir]
            return c.jhash, c.status
        return None, job.Status.MISSING


class _Main(PKDict):

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
                #TODO(robnagler) connect_timeout, max_message_size, ping_interval, ping_timeout
                c = await tornado.websocket.websocket_connect(cfg.supervisor_uri)
            except ConnectionRefusedError as e:
                await tornado.gen.sleep(_RETRY_SECS)
                continue
            m = self._format_reply(action=job.ACTION_READY_FOR_WORK)
            while True:
                try:
                    await c.write_message(m)
                #rn is this possible? We haven't closed it
                except tornado.websocket.WebSocketClosedError as e:
                    # TODO(e-carlin): Think about the failure handling more
                    pkdlog('closed{}', e)
                    break
                m = await c.read_message()
                pkdc('m={}', job.LogFormatter(m))
                if m is None:
                    break
                m = await self._op(m)

    async def _op(self, msg):
        try:
            m = pkjson.load_any(msg)
            m.run_dir = pkio.py_path(m.run_dir)
            r = await getattr(self, '_op_' + m.action)(m)
            return r or self._format_reply(m)
        except Exception as e:
            err = 'exception=' + str(e)
            stack = pkdexc()
            return self._format_reply(None, action=job.ACTION_ERROR, error=err, stack=stack)

    async def _op_cancel(self, msg):
        p = self._processes.get(msg.jid)
        if not p:
            return self._format_reply(msg, action=job.ACTION_ERROR, error='no such jid')
        await p.cancel()

    async def _op_kill(self, msg):
        self.kill()

    async def _op_status(self, msg):
        try:
            return self.format_reply(
                msg,
                agent_status=pkjson.load_any(msg.run_dir.join(_AGENT_FILE)),
            )
        except Exception:
            f = msg.run_dir.join(sirepo.job.RUNNER_STATUS_FILE)
            if not f.exists():
                return self.format_reply(msg, agent_status=None)
do not reply
        return self._format_reply(msg)

    async def _op_process(self, msg):
        p = _Process(msg=msg)
        self._processes[jid] = p
        await p.start()

    def _format_reply(self, msg, **kwargs):
        if msg:
            kwargs['op_id'] = msg.get('op_id')
            kwargs['jid'] = msg.get('jid')
        return pkjson.dump_bytes(
            PKDict(agent_id=cfg.agent_id, **kwargs),
        )
