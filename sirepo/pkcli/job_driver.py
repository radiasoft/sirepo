# -*- coding: utf-8 -*-
"""The runner daemon.

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function

import asyncio
import contextlib
from pykern import pkcollections, pkio, pkjson
from pykern.pkdebug import pkdlog, pkdp, pkdexc, pkdc, pkdlog
from sirepo import runner_client, runner_daemon
from sirepo.runner_daemon import local_process
import async_generator
import tornado.ioloop
import tornado.gen
import tornado.httpclient
import tornado.locks
import math
import contextlib

ACTION_READY_FOR_WORK = 'ready_for_work'
ACTION_REPORT_JOB_STARTED = 'report_job_started'
ACTION_PROCESS_RESULT = 'process_result'


_KILL_TIMEOUT_SECS = 3


def start():
    io_loop = tornado.ioloop.IOLoop.current()
    job_tracker = _JobTracker(io_loop)
    io_loop.spawn_callback(_main, io_loop, job_tracker)
    io_loop.start()

async def _main(io_loop, job_tracker):
    #TODO(e-carlin): This logic is annoying
    results = None
    while True:
        if results == None:
            with _catch_and_log_errors(Exception, 'error in _main with _notify_supervisor_ready_for_work'):
                results = await _notify_supervisor_ready_for_work(io_loop, job_tracker)
            if results == None:
                continue
        with _catch_and_log_errors(Exception, 'error in _main with _notify_results'):
            results = await _notify_supervisor_results(io_loop, job_tracker, results)


async def _notify_supervisor_results(io_loop, job_tracker, results):
    return await _notify_supervisor(io_loop, job_tracker, results)


async def _notify_supervisor_ready_for_work(io_loop, job_tracker):
    data = pkcollections.Dict({
        'action': ACTION_READY_FOR_WORK,
    })
    return await _notify_supervisor(io_loop, job_tracker, data)


async def _notify_supervisor(io_loop, job_tracker, data):
    #TODO(e-carlin): **kwargs
    try:
        data.source = 'driver'
        data.uid = 'sVKP0jmq' #TODO(e-carlin): This should not be here. The supervisor should tell us this on creation
        # body = {
        #     'source': 'driver',
        #     'uid': 'sVKP0jmq', #TODO(e-carlin): Make real id
        #     'action': action,
        #     'data': data
        # }
        pkdlog(f'Notifying supervisor: {data}')

        http_client = tornado.httpclient.AsyncHTTPClient()
        response = await http_client.fetch(
            'http://localhost:8888',
            method='POST',
            body=pkjson.dump_bytes(data),
            request_timeout=math.inf,
            )

        #TODO(e-carlin): Hack. When we send results to server it responds with nothing
        if response.body is b'':
            return None

        supervisor_request = pkcollections.Dict(pkjson.load_any(response.body))
        pkdp(f'Supervisor responded with: {supervisor_request}')

        #TODO(e-carlin): Better name? Here we move from response to request since the supervisor responds with a request
        return _process_supervisor_request(io_loop, job_tracker, supervisor_request)
    except Exception as e:
        pkdp(f'Exception notifying supervisor. Caused by: {e}')
        await tornado.gen.sleep(1) #TODO(e-carlin): Exponential backoff? We need to handle cases individually


def _process_supervisor_request(io_loop, job_tracker, request):
    if request.action == 'start_report_job':
        io_loop.spawn_callback(_start_report_job, io_loop, job_tracker, request)
        return pkcollections.Dict({
            'action': 'report_job_started',
            'request_id': request.request_id,
            'uid': request.uid,
        })
    assert 0

async def _start_report_job(io_loop, job_tracker, request):
    assert request.action == 'start_report_job'
    pkdc('start_report_job: {}', request)
    await job_tracker.start_report_job(
        pkio.py_path(request.run_dir), request.jhash,
        request.backend,
        request.cmd, pkio.py_path(request.tmp_dir),
    )

class _JobInfo:
    def __init__(self, run_dir, jhash, status, report_job):
        self.run_dir = run_dir
        self.jhash = jhash
        self.status = status
        self.report_job = report_job
        self.cancel_requested = False

class _JobTracker:
    def __init__(self, io_loop):
        self.report_jobs = {}
        self._io_loop = io_loop


    def run_dir_status(self, run_dir):
        """Get the current status of whatever's happening in run_dir.

        Returns:
        Tuple of (jhash or None, status of that job)

        """
        disk_in_path = run_dir.join('in.json')
        disk_status_path = run_dir.join('status')
        if disk_in_path.exists() and disk_status_path.exists():
            # status should be recorded on disk XOR in memory
            assert run_dir not in self.report_jobs
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
                disk_status = runner_client.JobStatus.ERROR
            return disk_jhash, runner_client.JobStatus(disk_status)
        elif run_dir in self.report_jobs:
            job_info = self.report_jobs[run_dir]
            return job_info.jhash, job_info.status
            
        return None, runner_client.JobStatus.MISSING


    async def start_report_job(self, run_dir, jhash, backend, cmd, tmp_dir):
        # First make sure there's no-one else using the run_dir
        current_jhash, current_status = self.run_dir_status(run_dir)
        if current_status is runner_client.JobStatus.RUNNING:
            # Something's running.
            if current_jhash == jhash:
                # It's already the requested job, so we have nothing to
                # do. Throw away the tmp_dir and move on.
                pkdlog(
                    'job is already running; skipping (run_dir={}, jhash={}, tmp_dir={})',
                    run_dir, jhash, tmp_dir,
                )
                pkio.unchecked_remove(tmp_dir)
                return
            # It's some other job. Better kill it before doing
            # anything else.
            # XX TODO: should we check some kind of sequence number
            # here? I don't know how those work.
            #TODO(robnagler) it's not "stale", but it is running. There's no need for
            #    sequence numbers. This should never happen, and the supervisor should
            #    should be informed of this situation, because it holds the queue,
            #    and it wouldn't start a job that is already running.
            pkdlog(
                'stale job is still running; killing it (run_dir={}, jhash={})',
                run_dir,
                jhash,
            )
            await self.kill_all(run_dir)

        # Okay, now we have the dir to ourselves. Set up the new run_dir:
        assert run_dir not in self.report_jobs
        #TODO(robnagler): this has to be atomic.
        pkio.unchecked_remove(run_dir)
        tmp_dir.rename(run_dir)
        report_job = local_process.start_report_job(run_dir, cmd) # TODO(e-carlin): Handle multiple backends
        job_info = _JobInfo(
            run_dir, jhash, runner_client.JobStatus.RUNNING, report_job
        )
        self.report_jobs[run_dir] = job_info

        self._io_loop.spawn_callback(
            self._supervise_report_job, run_dir, jhash, job_info
        )
        
    async def _supervise_report_job(self, run_dir, jhash, job_info):
        with _catch_and_log_errors(Exception, 'error in _supervise_report_job'):
            # Make sure returncode is defined in the finally block, even if
            # wait() somehow crashes
            returncode = None
            try:
                returncode = await job_info.report_job.wait_for_exit()
            finally:
                # Clear up our in-memory status
                assert self.report_jobs[run_dir] is job_info
                del self.report_jobs[run_dir]
                # Write status to disk
                if job_info.cancel_requested:
                    _write_status(runner_client.JobStatus.CANCELED, run_dir)
                    await self.run_extract_job(
                        run_dir, jhash, 'remove_last_frame', '[]',
                    )
                elif returncode == 0:
                    _write_status(runner_client.JobStatus.COMPLETED, run_dir)
                else:
                    pkdlog(
                        '{} {}: job failed, returncode = {}',
                        run_dir, jhash, returncode,
                    )
                    _write_status(runner_client.JobStatus.ERROR, run_dir)

# Cut down version of simulation_db.write_result
def _write_status(status, run_dir):
    fn = run_dir.join('result.json')
    if not fn.exists():
        pkjson.dump_pretty({'state': status.value}, filename=fn)
        pkio.write_text(run_dir.join('status'), status.value)

@contextlib.contextmanager
def _catch_and_log_errors(exc_type, msg, *args, **kwargs):
    try:
        yield
    except exc_type:
        pkdlog(msg, *args, **kwargs)
        pkdlog(pkdexc())