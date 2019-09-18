# -*- coding: utf-8 -*-
"""Agent for managing the execution of jobs.

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function

from pykern import pkcollections, pkio, pkjson, pkconfig
from pykern.pkdebug import pkdlog, pkdp, pkdexc, pkdc, pkdlog
from sirepo import job
from sirepo import job_supervisor_client
from sirepo import job_supervisor_client
#rn load dynamically
from sirepo.job_driver_backends import local_process
from sirepo.pkcli import job_supervisor
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


_RUNNER_INFO_BASENAME = 'runner-info.json'
_KILL_TIMEOUT_SECS = 3

#rn let's pass these in environment variables, then we can
# just use pkconfig.
def start(agent_id, supervisor_uri):
#rn I don't think these should be globals. Rather
#   pass them as state perhaps in the
    io_loop = tornado.ioloop.IOLoop.current()
    io_loop.spawn_callback(
        _Msg(agent_id=agent_id, supervisor_uri=supervisor_uri).loop,
    )
    io_loop.start()

#rn _main is not clear. This should be called _connect_to_supervisor
#async def _main():
#    await _connect_to_supervisor()
#    await

def _Msg(pkcollections.Dict):

    def loop():
        self.job_tracker = _JobTracker()
        while True:
            self.current_msg = None
            try:
                #TODO(robnagler) connect_timeout, max_message_size, ping_interval, ping_timeout
                c = await websocket_connect(_SUPERVISOR_URI)
            except ConnectionRefusedError as e:
                pkdlog('{} uri=', e, _SUPERVISOR_URI)
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
                m = await conn.read_message()
                if m is None:
                    break
                m = await self._dispatch(m)

    async def _dispatch(self, msg):
#rn not sure I like rid in this context. Rather req_id. Like sim_id
# should be used instead of simulationId
        try:
            m, err = self._parse_req(msg)
            if not err:
                self.current_msg = m
                pkdlog('action={action} request_id={rid}', **m)
                pkdc(m)
                return await getattr(self, '_dispatch_' + m.action)(m)
        except Exception as e:
            err = 'exception=' + str(e)
        return self._format_reply(action='protocol_error', error=err, msg=msg)

#rn maybe this should just be "cancel" since everything is a "job"
    async def _dispatch_cancel_compute_job(self, msg):
        jhash, status = self.job_tracker.run_dir_status(msg.run_dir)
        if jhash == request.jhash:
            await self.job_tracker.kill(request.run_dir)
        return self._format_reply()

#rn maybe this should just be "_compute"
    async def _dispatch_compute_job(job_tracker, message):
        await job_tracker.start_compute_job(
            message.run_dir, message.jhash,
            message.backend,
            message.cmd, message.tmp_dir,
        )
        return self._format_reply(
            action=job.ACTION_COMPUTE_JOB_STARTED,
        )

    async def _dispatch_run_extract_job(self, msg):
        res = await self.job_tracker.run_extract_job(
            msg.run_dir,
            msg.jhash,
            msg.subcmd,
            msg.arg,
        )
        return self._format_reply(
#rn this seems superfluous, since we are matching req_id in the supervisor,
#  which is more secure for the supervisor anyway. Agent shouldn't be able
#  to direct the results to anything else
# I think a message in response should be "ok" or not. With some data
# The "ok" can be implicit.
            action=job.ACTION_EXTRACT_JOB_RESULTS,
            result=res,
        )

    async def _dispatch_job_status(self, msg):
        res = await self.job_tracker.compute_job_status(msg.run_dir, msg.jhash)
        return self._format_reply(
            action=job.ACTION_COMPUTE_JOB_STATUS,
            status=res.value,
        )

    def _format_reply(self, **kwargs)
        msg.agent_id = self.agent_id
        if self.current_msg:
#rn use get() because there may be an error in the sending message
# and we really don't want to get any errors
            msg.rid = self.current_msg.get('rid')
        return pkjson.dump_bytes(msg)

    def _parse_req(self, msg):
        try:
            m = pkjson.load_any(msg)
            for k, v in m.items():
                if k.endswith('_dir'):
                    m[k] = pkio.py_path(v)
        except Exception as e:
            return None, f'exception={e}'
        return m, None


class _JobTracker:
    def __init__(self):
        self._compute_jobs = pkcollections.Dict()

    async def kill(self, run_dir):
        """Kill job currently running in run_dir.

        Assumes that you've already checked what those jobs are (perhaps by
        calling run_dir_status), and decided they need to die.

        """
        compute_job = self._compute_jobs[run_dir]
        if compute_job.status is not job_supervisor_client.JobStatus.RUNNING:
            return
        pkdlog(
            'kill: killing job with jhash {} in {}',
            compute_job.jhash, run_dir,
        )
        compute_job.cancel_requested = True
        await compute_job.kill(_KILL_TIMEOUT_SECS)

    async def run_extract_job(self, run_dir, jhash, subcmd, arg):
        pkdc('{} {}: {} {}', run_dir, jhash, subcmd, arg)
        status = await self.compute_job_status(run_dir, jhash)
        if status is job_supervisor_client.JobStatus.MISSING:
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
                run_dir, jhash,
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

    async def start_compute_job(self, run_dir, jhash, backend, cmd, tmp_dir):
        current_jhash, current_status = self._run_dir_status(run_dir)
        if current_status is job_supervisor_client.JobStatus.RUNNING:
            if current_jhash == jhash:
                pkdlog(
                    'job is already running; skipping (run_dir={}, jhash={}, tmp_dir={})',
                    run_dir, jhash, tmp_dir,
                )
                pkio.unchecked_remove(tmp_dir)
                return
            else:
                pkdlog(
                    'job is still running; killing it (run_dir={}, jhash={})',
                    run_dir, jhash,
                )
                await self.kill(run_dir)

        assert run_dir not in self._compute_jobs
        pkio.unchecked_remove(run_dir)
        tmp_dir.rename(run_dir)
        job = local_process.ComputeJob(run_dir, jhash, job_supervisor_client.JobStatus.RUNNING, cmd)
        self._compute_jobs[run_dir] = job
        tornado.ioloop.IOLoop.current().spawn_callback(
           self._on_compute_job_exit,
           run_dir,
           job
        )

    async def _on_compute_job_exit(self, run_dir, compute_job):
        # with _catch_and_log_errors(Exception, 'error in _supervise_report_job'):
        # Make sure returncode is defined in the finally block, even if
        # wait() somehow crashes
        returncode = None
        try:
            returncode = await compute_job.wait_for_exit()
        finally:
            # Clear up our in-memory status
            assert self._compute_jobs[run_dir] is compute_job
            del self._compute_jobs[run_dir]
            # Write status to disk
            if compute_job.cancel_requested:
                _write_status(job_supervisor_client.JobStatus.CANCELED, run_dir)
                await self.run_extract_job(
                    run_dir, compute_job.jhash, 'remove_last_frame', '[]',
                )
            elif returncode == 0:
                _write_status(job_supervisor_client.JobStatus.COMPLETED, run_dir)
            else:
                pkdlog(
                    '{} {}: job failed, returncode = {}',
                    run_dir, compute_job.jhash, returncode,
                )
                _write_status(job_supervisor_client.JobStatus.ERROR, run_dir)

    async def compute_job_status(self, run_dir, jhash):
        """Get the current status of a specific job in the given run_dir."""
        status = job_supervisor_client.JobStatus.MISSING
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
                disk_status = job_supervisor_client.JobStatus.ERROR
            return disk_jhash, job_supervisor_client.JobStatus(disk_status)
        elif run_dir in self._compute_jobs:
            compute_job = self._compute_jobs[run_dir]
            return compute_job.jhash, compute_job.status

        return None, job_supervisor_client.JobStatus.MISSING


def _write_status(status, run_dir):
    fn = run_dir.join('result.json')
    if not fn.exists():
        pkjson.dump_pretty({'state': status.value}, filename=fn)
        pkio.write_text(run_dir.join('status'), status.value)
