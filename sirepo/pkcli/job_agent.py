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
from sirepo import job, simulation_db
from sirepo import job_agent_process
import sys
import tornado.gen
import tornado.httpclient
import tornado.ioloop
import tornado.locks
import tornado.queues
import tornado.websocket


_KILL_TIMEOUT_SECS = 3

_RETRY_SECS = 1

_INFO_FILE = 'job.json'

_INFO_VERSION = 1

_EXTRACT_ARG_FILE = 'extract-{}.json'

cfg = None


def default_command():
    job_supervisor.init()
    global cfg

    cfg = pkconfig.init(
        agent_id=pkconfig.Required(str, 'id of this agent'),
        supervisor_uri=pkconfig.Required(str, 'how to connect to the supervisor'),
    )
    pkdlog('{}', cfg)
    i = tornado.ioloop.IOLoop.current()
    i.spawn_callback(_Main()loop)
    i.start()


class _JobTracker:
    def __init__(self):
        self._compute_jobs = pkcollections.Dict()

    async def kill(self, msg):
        j = self._compute_jobs.get(run_dir)
        if j is None:
            pkdlog('not found in _compute_jobs msg={}', job.LogFormatter(msg))
            return
        if j.status != job.Status.RUNNING:
            pkdlog('status={} should be RUNNING msg={}', j.status, job.LogFormatter(msg))
            return
        pkdlog('killing msg={}', job.LogFormatter(msg))
        j.cancel_requested = True
        await j.kill(_KILL_TIMEOUT_SECS)

    async def run_extract_job(self, msg):
        pkdc('{}', job.LogFormatter(msg))
        s = await self.compute_job_status(msg)
        if s is job.Status.MISSING:
            pkdlog(
                'skipping, because no status file msg={}',
                job.LogFormatter(msg),
            )
            return PKDict()
        f = msg.run_dir.join(_EXTRACT_ARG_FILE.format(cfg.agent_id))
        pkjson.dump_pretty(msg.get('arg'), filename=f, pretty=False)
        r = await job_agent_process.run_extract_job(
            msg.run_dir,
            ['sirepo', 'extract', msg.cmd, str(f)],
        )
        if r.stderr:
            pkdlog(
                'msg={} stderr={}',
                job.LogFormatter(msg),
                r.stderr.decode('utf-8', errors='ignore'),
            )
        if r.returncode != 0:
            pkdlog(
                'error msg={} returncode={} stdout={}',
                job.LogFormatter(msg),
                r.returncode,
                r.stdout.decode('utf-8', errors='ignore'),
            )
            raise RuntimeError('command error')
        return pkjson.load_any(result.stdout)

    async def start_compute_job(self, msg):
        j, s = self._run_dir_status(msg)
        if s is job.Status.RUNNING:
            if j == jhash:
                pkdlog(
                    'ignoring already running; msg={}',
                    job.LogFormatter(msg),
                )
                pkio.unchecked_remove(msg.tmp_dir)
                return
        assert run_dir not in self._compute_jobs
        pkio.unchecked_remove(run_dir)
        tmp_dir.rename(run_dir)
        j = job_agent_process.ComputeJob(run_dir, jhash, job.Status.RUNNING, cmd)
        self._compute_jobs[run_dir] = j
        tornado.ioloop.IOLoop.current().spawn_callback(
           self._on_compute_job_exit,
           run_dir,
            j,
        )

    async def _on_compute_job_exit(self, run_dir, compute_job):
        returncode = None
        try:
            returncode = await compute_job.wait_for_exit()
        finally:
            # Clear up our in-memory status
            assert self._compute_jobs[run_dir] is compute_job
            del self._compute_jobs[run_dir]
            # Write status to disk
            if compute_job.cancel_requested:
                simulation_db.write_result(PKDict(state='canceled'), run_dir=run_dir)
                await self.run_extract_job(
                    PKDict(
                        cmd='remove_last_frame',
                        jhash=compute_job.jhash,
                        run_dir=run_dir,
                    ),
                )
            elif returncode == 0:
                simulation_db.write_result(PKDict(state='completed'), run_dir=run_dir)
            else:
                pkdlog(
                    '{} {}: job failed, returncode = {}',
                    run_dir, compute_job.jhash, returncode,
                )
                simulation_db.write_result(PKDict(state='error'), run_dir=run_dir)

    async def compute_job_status(self, msg):
        """Get the current status of a specific job in the given run_dir."""
        j, s = self._run_dir_status(msg)
        return s if j == msg.jhash else job.Status.MISSING

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
    async def loop(self):
        self.job_tracker = _JobTracker()
        while True:
            self.current_msg = None
            try:
                #TODO(robnagler) connect_timeout, max_message_size, ping_interval, ping_timeout
                c = await tornado.websocket.websocket_connect(cfg.supervisor_uri)
            except ConnectionRefusedError as e:
                pkdlog('{} uri=', e, cfg.supervisor_uri)
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
                m = await self._dispatch(m)

    async def _dispatch(self, msg):
        try:
            m, err = self._parse_req(msg)
            if not err:
                self.current_msg = m
                pkdlog('action={action} req_id={req_id}', **m)
                pkdc('{}', job.LogFormatter(m))
                return await getattr(self, '_dispatch_' + m.action)(m)
        except Exception as e:
            err = 'exception=' + str(e)
            pkdlog(pkdexc())
        return self._format_reply(action=job.ACTION_ERROR, error=err, msg=msg)

    #rn maybe this should just be "cancel" since everything is a "job"
    async def _dispatch_cancel_job(self, msg):
        j, _ = self.job_tracker._run_dir_status(msg)
        if j == msg.jhash:
            await self.job_tracker.kill(msg)
        return self._format_reply()

    async def _dispatch_compute_job_status(self, msg):
        return self._format_reply(
            status=await self.job_tracker.compute_job_status(msg).value,
        )

#rn need to distinguish between terminate and killing the process
#   i think you have to kill the subprocess
    async def _dispatch_kill(self, msg):
        # TODO(e-carlin): This is aggressive. Should we try to  check if there
        # is a running job and terminate it gracefully?
        tornado.ioloop.IOLoop.current().stop()

    async def _dispatch_run_extract_job(self, msg):
        self._format_reply(
            result=await self.job_tracker.run_extract_job(msg),
        )
        return

#rn maybe this should just be "_compute"
    async def _dispatch_start_compute_job(self, msg):
        await self.job_tracker.start_compute_job(msg)
        return self._format_reply()

    def _format_reply(self, **kwargs):
        msg = PKDict(agent_id=cfg.agent_id, **kwargs)
        if self.current_msg:
            msg.req_id = self.current_msg.get('req_id')
        return pkjson.dump_bytes(msg)

    def _parse_req(self, msg):
        try:
            m = pkjson.load_any(msg)
            for k, v in m.items():
                if k.endswith('_dir'):
                    m[k] = pkio.py_path(v)
        except Exception as e:
            pkdlog('Error: {}\n{}', e, pkdexc())
            return None, f'exception={e}'
        return m, None
