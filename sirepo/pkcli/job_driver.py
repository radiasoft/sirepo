# -*- coding: utf-8 -*-
"""Driver for managing the execution of jobs.

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function

from pykern import pkcollections, pkio, pkjson
from pykern.pkdebug import pkdlog, pkdp, pkdexc, pkdc, pkdlog
from sirepo import job_common
from sirepo import job_supervisor_client
from sirepo.pkcli import job_supervisor
from sirepo.job_driver_backends import local_process
import async_generator
import asyncio
import contextlib
import contextlib
import math
import tornado.gen
import tornado.httpclient
import tornado.ioloop
import tornado.locks
import tornado.queues


ACTION_KEEP_ALIVE = 'keep_alive'
ACTION_PROCESS_RESULT = 'process_result'
ACTION_READY_FOR_WORK = 'ready_for_work'
ACTION_REPORT_JOB_STARTED = 'report_job_started'

_RUNNER_INFO_BASENAME = 'runner-info.json'

_DRIVER_RESPONSES_Q = tornado.queues.Queue()
_SERVER_REQUESTS_Q = tornado.queues.Queue()

_UID = None


def start(uid):
    global _UID
    _UID = uid
    io_loop = tornado.ioloop.IOLoop.current()
    job_tracker = _JobTracker(io_loop)
    io_loop.spawn_callback(_notify_supervisor_ready_for_work, io_loop, job_tracker)
    io_loop.start()


@contextlib.contextmanager
def _catch_and_log_errors(exc_type, msg, *args, **kwargs):
    try:
        yield
    except exc_type:
        pkdlog(msg, *args, **kwargs)
        pkdlog(pkdexc())


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

    def report_job_status(self, run_dir, jhash):
        """Get the current status of a specific job in the given run_dir.

        """
        run_dir_jhash, run_dir_status = self.run_dir_status(run_dir)
        if run_dir_jhash == jhash:
            return run_dir_status
        else:
            return job_supervisor_client.JobStatus.MISSING

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
                disk_status = job_supervisor_client.JobStatus.ERROR
            return disk_jhash, job_supervisor_client.JobStatus(disk_status)
        elif run_dir in self.report_jobs:
            job_info = self.report_jobs[run_dir]
            return job_info.jhash, job_info.status
            
        return None, job_supervisor_client.JobStatus.MISSING
    
    async def run_extract_job(self, io_loop, run_dir, jhash, subcmd, arg):
        pkdc('{} {}: {} {}', run_dir, jhash, subcmd, arg)
        status = self.report_job_status(run_dir, jhash)
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
           io_loop, run_dir, cmd, runner_info.backend_info,
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


    async def start_report_job(self, io_loop, run_dir, jhash, backend, cmd, tmp_dir):
        assert run_dir not in self.report_jobs
        #TODO(robnagler): this has to be atomic.
        pkio.unchecked_remove(run_dir)
        tmp_dir.rename(run_dir)
        report_job = local_process.start_report_job(run_dir, cmd) # TODO(e-carlin): Handle multiple backends
        job_info = _JobInfo(
            run_dir, jhash, job_supervisor_client.JobStatus.RUNNING, report_job
        )
        self.report_jobs[run_dir] = job_info

        await self._supervise_report_job(io_loop, run_dir, jhash, job_info)
        
    async def _supervise_report_job(self, io_loop, run_dir, jhash, job_info):
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
                    _write_status(job_supervisor_client.JobStatus.CANCELED, run_dir)
                    await self.run_extract_job(
                        io_loop, run_dir, jhash, 'remove_last_frame', '[]',
                    )
                elif returncode == 0:
                    _write_status(job_supervisor_client.JobStatus.COMPLETED, run_dir)
                else:
                    pkdlog(
                        '{} {}: job failed, returncode = {}',
                        run_dir, jhash, returncode,
                    )
                    _write_status(job_supervisor_client.JobStatus.ERROR, run_dir)


async def _notify_supervisor(data):
    data.source = 'driver'
    data.uid = _UID 
    #TODO(e-carlin): This is ugly
    pkdlog('Notifying supervisor: {}',  {x: data[x] for x in data if x not in ['result', 'arg']})
    pkdc('Full body: {}', data)

    http_client = tornado.httpclient.AsyncHTTPClient()
    response = await http_client.fetch(
        job_common.job_driver_cfg.supervisor_uri,
        method='POST',
        body=pkjson.dump_bytes(data),
        request_timeout=math.inf,
        )

    supervisor_request = pkcollections.Dict(pkjson.load_any(response.body))
    pkdc('Supervisor responded with: {}', supervisor_request)
    return supervisor_request


async def _notify_supervisor_ready_for_work(io_loop, job_tracker):
    while True:
        data = pkcollections.Dict({
            'action': ACTION_READY_FOR_WORK,
        })
        try:
            request = await _notify_supervisor(data)
        except ConnectionRefusedError as e:
            pkdlog('Connection refused while calling supervisor ready_for_work. \
                Sleeping and trying again. Caused by: {}', e)
            await tornado.gen.sleep(1)    
            continue
        if request.action == ACTION_KEEP_ALIVE:
            continue
        io_loop.spawn_callback(_process_supervisor_request, io_loop, job_tracker, request)


async def _process_supervisor_request(io_loop, job_tracker, request):
    #TODO(e-carlin): This code is repetitive. We can find the function name from the reuqest action
    if request.action == 'start_report_job':
        pkdc('start_report_job: {}', request)
        results = await _start_report_job(job_tracker, request, io_loop)
        await _notify_supervisor(results)
        return
    elif request.action == 'report_job_status':
        pkdc('report_job_status: {}', request)
        status = _report_job_status(job_tracker, request)
        await _notify_supervisor(status)
        return
    elif request.action == 'run_extract_job':
        pkdc('run_extract_job: {}', request)
        results = await _run_extract_job(job_tracker, request, io_loop)
        await _notify_supervisor(results)
        return
    else:
        raise Exception(f'Request.action {request.action} unknown')
    

def _report_job_status(job_tracker, request):
    pkdc('report_job_status: {}', request)
    status =  job_tracker.report_job_status(
        #TODO(e-carlin): Find a common place to do pkio.py_path() these are littered around
        pkio.py_path(request.run_dir), request.jhash
    ).value
    return pkcollections.Dict({
        'action': 'status_of_report_job',
        'request_id': request.request_id,
        'uid': request.uid,
        'status': status,
    })
            

async def _run_extract_job(job_tracker, request, io_loop):
    pkdc('run_extrac_job: {}', request)
    result = await job_tracker.run_extract_job(
        io_loop,
        pkio.py_path(request.run_dir),
        request.jhash,
        request.subcmd,
        request.arg,
    )
    return pkcollections.Dict({
        'action' : 'result_of_run_extract_job',
        'request_id': request.request_id,
        'uid': request.uid,
        'result': result,
    })


async def _start_report_job(job_tracker, request, io_loop):
    pkdc('start_report_job: {}', request)
    await job_tracker.start_report_job(
        io_loop,
        pkio.py_path(request.run_dir), request.jhash,
        request.backend,
        request.cmd, pkio.py_path(request.tmp_dir),
    )
    return pkcollections.Dict({
        'action': 'report_job_started',
        'request_id': request.request_id,
        'uid': request.uid,
    })


def _write_status(status, run_dir):
    fn = run_dir.join('result.json')
    if not fn.exists():
        pkjson.dump_pretty({'state': status.value}, filename=fn)
        pkio.write_text(run_dir.join('status'), status.value)

