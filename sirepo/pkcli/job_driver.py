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
ACTION_PROCESS_RESULT = 'process_result'


_KILL_TIMEOUT_SECS = 3


def start():
    io_loop = tornado.ioloop.IOLoop.current()
    io_loop.spawn_callback(_main, io_loop)
    io_loop.start()

async def _main(io_loop):
    job_tracker = _JobTracker(io_loop)
    io_loop.spawn_callback(_notify_supervisor_ready_for_work, io_loop, job_tracker)

async def _notify_supervisor_ready_for_work(io_loop, job_tracker):
    while True:
        await _notify_supervisor(io_loop, job_tracker, ACTION_READY_FOR_WORK)


async def _notify_supervisor(io_loop, job_tracker, action, data={}):
    try:
        body = {
            'source': 'driver',
            'uid': 'sVKP0jmq', #TODO(e-carlin): Make real id
            'action': action,
            'data': data
        }
        pkdlog(f'Notifying supervisor: {body}')

        http_client = tornado.httpclient.AsyncHTTPClient()
        response = await http_client.fetch(
            'http://localhost:8888',
            method='POST',
            body=pkjson.dump_bytes(body),
            request_timeout=math.inf,
            )

        pkdp(f'Supervisor responded with: {pkcollections.Dict(pkjson.load_any(response.body))}')


        supervisor_request = pkcollections.Dict(pkjson.load_any(response.body))
        assert supervisor_request.action == 'start_report_job'
        #TODO(e-carlin): Better name? Here we move from response to request since the supervisor responds with a request
        io_loop.spawn_callback(_process_supervisor_request, io_loop, job_tracker, supervisor_request)
    except Exception as e:
        pkdp(f'Exception notifying supervisor. Caused by: {e}')
        await tornado.gen.sleep(1) #TODO(e-carlin): Exponential backoff? We need to handle cases individually


async def _process_supervisor_request(io_loop, job_tracker, request):
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

class _LockDict:
    from contextlib import contextmanager
    def __init__(self):
        # {key: ParkingLot}
        # lock is held iff the key exists
        self._waiters = {}

    #TODO(robnagler): i wonder if this needs to be an async_generator but
    #   i don't understand this well enough.
    @contextmanager
    async def __getitem__(self, key):
        if key not in self._waiters:
            self._waiters[key] = asyncio.Lock() # tornado locks don't have locked() so using asyncio
        a = False
        try:
            r = self._waiters[key].locked()
            pkdp(f'*** Result of locked {r}')
            await self._waiters[key].acquire()
            a = True
            yield
        finally:
            if a:
                ### release_if_owner would make this simpler or
                ### at least current_task_is_owner?
                self._waiters[key].release()
                #TODO(e-carlin): Does this really work? These calls are atomic so
                # I would guess that no one else has the time to call acquire?
                if not self._waiters[key].locked():
                    del self._waiters[key]

class _JobTracker:
    def __init__(self, io_loop):
        self.report_jobs = {}
        self.locks = _LockDict()
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

        # TODO(e-carlin): Real supervision is needed
        # async def _supervise_job(run_dir, jhash, job_info):
        #     pkdp(f'Starting to wait on jhash {jhash}')
        #     returncode = await job_info.report_job.wait_for_exit()
        #     pkdp(f'jhash {jhash} finished with exit code {returncode}')

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
                pkdp('***** In finally')
                async with self.locks[run_dir]:
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
                    pkdp('*** Done with finally')

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