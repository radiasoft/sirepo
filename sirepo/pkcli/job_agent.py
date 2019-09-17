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


# TODO(e-carlin): Do we want this all in global state?
_AGENT_ID = None
_JOB_TRACKER = None
_SUPERVISOR_URI = None
_WS = None

_RUNNER_INFO_BASENAME = 'runner-info.json'
_KILL_TIMEOUT_SECS = 3

def start(agent_id, supervisor_uri):
    global _JOB_TRACKER, _SUPERVISOR_URI, _AGENT_ID
    _JOB_TRACKER = _JobTracker() 
    _SUPERVISOR_URI = supervisor_uri
    _AGENT_ID = agent_id
    io_loop = tornado.ioloop.IOLoop.current()
    io_loop.spawn_callback(_main)
    io_loop.start()

async def _main():
    await _connect_to_supervisor()
    await _send_to_supervisor(pkcollections.Dict({'action': job.ACTION_READY_FOR_WORK}))

async def _connect_to_supervisor():
    global _WS
    if _WS is None:
        try:
            _WS = await tornado.websocket.websocket_connect(
                _SUPERVISOR_URI,
                on_message_callback=_receive_from_supervisor,
            )
        except ConnectionRefusedError as e:
            pkdlog('ws connection refused. Caused by: {}', e)
            _WS = None
            await tornado.gen.sleep(1)
            await _connect_to_supervisor() 
    

def _receive_from_supervisor(message):
    pkdc('received message from supervisor {}', message)
    if message is None:
        # TODO(e-carlin): Do we need to remove callback to clean up after ourselves?
        # message is None indicates server closed connection
        tornado.ioloop.IOLoop.current().spawn_callback(_main)
        return
    m = pkjson.load_any(message)
    if 'run_dir' in m:
        m.run_dir = pkio.py_path(m.run_dir)
    if 'tmp_dir' in m:
        m.tmp_dir = pkio.py_path(m.tmp_dir)
    # TODO(e-carlin): Do we need to remove callback to clean up after ourselves?
    tornado.ioloop.IOLoop.current().spawn_callback(_handle_message, m)

_MESSAGE_HANDLERS = {}
def _message_handler(fn):
    _MESSAGE_HANDLERS[fn.__name__.lstrip('_')] = fn
    return fn


@_message_handler
async def _cancel_compute_job(job_tracker, request):
    jhash, status = job_tracker.run_dir_status(request.run_dir)
    if jhash == request.jhash:
        await job_tracker.kill(request.run_dir)
    return {}

@_message_handler
async def _run_extract_job(job_tracker, message):
    res = await job_tracker.run_extract_job(
        message.run_dir,
        message.jhash,
        message.subcmd,
        message.arg,
    )
    return pkcollections.Dict({
        'action' : job.ACTION_EXTRACT_JOB_RESULTS,
        'result': res,
    })

@_message_handler
async def _compute_job_status(job_tracker, message):
    pkdc('compute_job_status: {}', message)
    res = await job_tracker.compute_job_status(message.run_dir, message.jhash)
    return pkcollections.Dict({
        'action': job.ACTION_COMPUTE_JOB_STATUS,
        'status': res.value,
    }) 


@_message_handler
async def _start_compute_job(job_tracker, message):
    pkdc('start_compute_job: {}', message)
    await job_tracker.start_compute_job(
        message.run_dir, message.jhash,
        message.backend,
        message.cmd, message.tmp_dir,
    )
    return pkcollections.Dict({
        'action': job.ACTION_COMPUTE_JOB_STARTED,
    })

async def _handle_message(message):
        h = _MESSAGE_HANDLERS[message.action]
        res = await h(_JOB_TRACKER, message)
        await _send_to_supervisor(res, message)


async def _send_to_supervisor(res_message, req_message=None):
    global _WS
    try:
        res_message.agent_id = _AGENT_ID
        if req_message:
           res_message.rid = req_message.rid
        await _WS.write_message(pkjson.dump_bytes(res_message))
    except tornado.websocket.WebSocketClosedError:
        # TODO(e-carlin): Think about the failure handling more
        pkdlog('ws closed')
        _WS = None
        await _connect_to_supervisor()


class _JobTracker:
    def __init__(self):
        self._compute_jobs = {}

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
