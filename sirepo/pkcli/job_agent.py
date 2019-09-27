# -*- coding: utf-8 -*-
"""Agent for managing the execution of jobs.

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkcollections, pkio, pkjson, pkconfig
from pykern.pkdebug import pkdlog, pkdp, pkdexc, pkdc, pkdlog
from sirepo import job, simulation_db
# TODO(e-carlin): load dynamically
from sirepo.job_driver_backends import local_process
import async_generator
import asyncio
import contextlib
import contextlib
import functools
import math
import tornado.gen
import tornado.httpclient
import tornado.ioloop
import tornado.locks
import tornado.queues
import tornado.websocket


_KILL_TIMEOUT_SECS = 3
_RETRY_DELAY = 1
_RUNNER_INFO_BASENAME = 'runner-info.json'


def start():
    cfg = pkconfig.init(
        agent_id=('abc123', str, 'the id of the agent'),
        job_server_ws_uri=(job.cfg.job_server_ws_uri, str, 'the uri to connect to the job server on'),
    )
    pkdlog('agent_id={}', cfg.agent_id)
    io_loop = tornado.ioloop.IOLoop.current()
    io_loop.spawn_callback(
        _Msg(agent_id=cfg.agent_id, job_server_ws_uri=cfg.job_server_ws_uri).loop,
    )
    io_loop.start()


class _JobTracker:
    def __init__(self):
        self._compute_jobs = pkcollections.Dict()

    async def kill(self, run_dir):
        j = self._compute_jobs.get(run_dir)
        if j is None: # TODO(e-carlin): This can probably be removed since supervisor will never send a cancel in this case
            return
        if j.status is not job.JobStatus.RUNNING: # TODO(e-carlin): This can probably be removed since supervisor will never send a cancel in this case
            return
        pkdlog(
            'job with jhash {} in {}',
            j.jhash, run_dir,
        )
        j.cancel_requested = True
        await j.kill(_KILL_TIMEOUT_SECS)

    async def run_extract_job(self, run_dir, jhash, subcmd, arg):
        pkdc('{} {}: {} {}', run_dir, jhash, subcmd, arg)
        status = await self.compute_job_status(run_dir, jhash)
        if status is job.JobStatus.MISSING:
            pkdlog('{} {}: report is missing; skipping extract job',
                   run_dir, jhash)
            return {}
        #rn do we want this?
        # figure out which backend and any backend-specific info
        runner_info_file = run_dir.join(_RUNNER_INFO_BASENAME)
        if runner_info_file.exists():
            runner_info = pkjson.load_any(runner_info_file)
        else:
            # Legacy run_dir
            runner_info = pkcollections.Dict(
                version=1, backend='local', backend_info={},
            )
        assert runner_info.version == 1

        # run the job
        cmd = ['sirepo', 'extract', subcmd, arg]
        result = await local_process.run_extract_job( #TODO(e-carlin): Handle multiple backends
           run_dir, cmd, runner_info.backend_info,
        )

        if result.stderr:
            pkdlog(
                'got output on stderr ({} {}):\n{}',
                run_dir,
                jhash,
                result.stderr.decode('utf-8', errors='ignore'),
            )

        if result.returncode != 0:
            pkdlog(
                'failed with return code {} ({} {}), stdout:\n{}',
                result.returncode,
                run_dir,
                subcmd,
                result.stdout.decode('utf-8', errors='ignore'),
            )
            raise AssertionError

        return pkjson.load_any(result.stdout)

    async def start_compute_job(self, run_dir, jhash, cmd, tmp_dir):
        current_jhash, current_status = self._run_dir_status(run_dir)
        if current_status is job.JobStatus.RUNNING:
            if current_jhash == jhash:
                pkdlog(
                    'job is already running; skipping (run_dir={}, jhash={}, tmp_dir={})',
                    run_dir, jhash, tmp_dir,
                )
                pkio.unchecked_remove(tmp_dir)
                return
        assert run_dir not in self._compute_jobs
        pkio.unchecked_remove(run_dir)
        tmp_dir.rename(run_dir)
        j = local_process.ComputeJob(run_dir, jhash, job.JobStatus.RUNNING, cmd)
        self._compute_jobs[run_dir] = j
        tornado.ioloop.IOLoop.current().spawn_callback(
           self._on_compute_job_exit,
           run_dir,
           j
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
                simulation_db.write_result({'state': 'canceled'}, run_dir=run_dir)
                await self.run_extract_job(
                    run_dir, compute_job.jhash, 'remove_last_frame', '[]',
                )
            elif returncode == 0:
                simulation_db.write_result({'state': 'completed'}, run_dir=run_dir)
            else:
                pkdlog(
                    '{} {}: job failed, returncode = {}',
                    run_dir, compute_job.jhash, returncode,
                )
                simulation_db.write_result({'state': 'error'}, run_dir=run_dir)

    async def compute_job_status(self, run_dir, jhash):
        """Get the current status of a specific job in the given run_dir."""
        status = job.JobStatus.MISSING
        run_dir_jhash, run_dir_status = self._run_dir_status(run_dir)
        if run_dir_jhash == jhash:
            status = run_dir_status
        return status

    def _run_dir_status(self, run_dir):
        """Get the current status of whatever's happening in run_dir.

        Returns:
        Tuple of (jhash or None, status of that job)

        """
        disk_in_path = run_dir.join('in.json')
        disk_status_path = run_dir.join('status')
        if disk_in_path.exists() and disk_status_path.exists():
            # status should be recorded on disk XOR in memory
            assert run_dir not in self._compute_jobs
            disk_in_text = pkio.read_text(disk_in_path)
            disk_jhash = pkjson.load_any(disk_in_text).reportParametersHash
            disk_status = pkio.read_text(disk_status_path)
            if disk_status == 'pending':
                # We never write this, so it must be stale, in which case
                # the job is no longer pending...
                pkdlog(
                    'found "pending" status, treating as "error" ({})',
                    disk_status_path,
                )
                disk_status = job.JobStatus.ERROR
            return disk_jhash, job.JobStatus(disk_status)
        elif run_dir in self._compute_jobs:
            compute_job = self._compute_jobs[run_dir]
            return compute_job.jhash, compute_job.status

        return None, job.JobStatus.MISSING

class _Msg(pkcollections.Dict):
    async def loop(self):
        self.job_tracker = _JobTracker()
        while True:
            self.current_msg = None
            try:
                #TODO(robnagler) connect_timeout, max_message_size, ping_interval, ping_timeout
                c = await tornado.websocket.websocket_connect(self.job_server_ws_uri)
            except ConnectionRefusedError as e:
                pkdlog('{} uri=', e, self.job_server_ws_uri)
                await tornado.gen.sleep(_RETRY_DELAY)
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
                pkdc('m={}', m)
                if m is None:
                    break
                m = await self._dispatch(m)

    async def _dispatch(self, msg):
        try:
            m, err = self._parse_req(msg)
            if not err:
                self.current_msg = m
                pkdlog('action={action} req_id={req_id}', **m)
                pkdc(m)
                return await getattr(self, '_dispatch_' + m.action)(m)
        except Exception as e:
            err = 'exception=' + str(e)
            pkdlog(pkdexc())
        return self._format_reply(action='protocol_error', error=err, msg=msg)

    #rn maybe this should just be "cancel" since everything is a "job"
    async def _dispatch_cancel_job(self, msg):
        jhash, _ = self.job_tracker._run_dir_status(msg.run_dir)
        if jhash == msg.jhash:
            await self.job_tracker.kill(msg.run_dir)
        return self._format_reply()

    async def _dispatch_compute_job_status(self, msg):
        res = await self.job_tracker.compute_job_status(msg.run_dir, msg.jhash)
        return self._format_reply(status=res.value)

    async def _dispatch_run_extract_job(self, msg):
        res = await self.job_tracker.run_extract_job(
            msg.run_dir,
            msg.jhash,
            msg.subcmd,
            msg.arg,
        )
        return self._format_reply(result=res)

    #rn maybe this should just be "_compute"
    async def _dispatch_start_compute_job(self, msg):
        await self.job_tracker.start_compute_job(
            msg.run_dir,
            msg.jhash,
            msg.cmd,
            msg.tmp_dir,
        )
        return self._format_reply()

    def _format_reply(self, **kwargs):
        msg = pkcollections.Dict(
            kwargs,
            agent_id = self.agent_id
        )
        if self.current_msg:
            #rn use get() because there may be an error in the sending message
            # and we really don't want to get any errors
            msg.req_id = self.current_msg.get('req_id')
        return pkjson.dump_bytes(msg)

    def _parse_req(self, msg):
        try:
            m = pkjson.load_any(msg)
            for k, v in m.items():
                if k.endswith('_dir'):
                    m[k] = pkio.py_path(v)
        except Exception as e:
            pkdlog('Error: {}', e)
            pkdp(pkdexc())
            return None, f'exception={e}'
        return m, None

