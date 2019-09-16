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
from sirepo.job_driver_backends import local_process
from sirepo.pkcli import job_supervisor
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


# TODO(e-carlin): Do we want this all in global state?
_AGENT_ID = None
_JOB_TRACKER = None
_SUPERVISOR_URI = None
_WS = None


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
    await _send_to_supervisor(pkcollections.Dict({'action': job.ACTION_DRIVER_READY_FOR_WORK}))

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
        # message is None indicates server closed connection
        tornado.ioloop.IOLoop.current().spawn_callback(_main)
        return
    m = pkjson.load_any(message)
    if 'run_dir' in m:
        m.run_dir = pkio.py_path(m.run_dir)
    if 'tmp_dir' in m:
        m.tmp_dir = pkio.py_path(m.tmp_dir)
    _JOB_TRACKER.pending_requests.put_nowait(m)

async def _send_to_supervisor(message, request=None):
    global _WS
    try:
        message.agent_id = _AGENT_ID
        if request:
           message.rid = request.rid
        await _WS.write_message(pkjson.dump_bytes(message))
    except tornado.websocket.WebSocketClosedError:
        # TODO(e-carlin): Think about the failure handling more
        pkdlog('ws closed')
        _WS = None
        await _connect_to_supervisor()
        await _send_to_supervisor(message)


class _JobTracker:
    def __init__(self):
        self._report_jobs = {}
        self.pending_requests = tornado.queues.Queue()
        tornado.ioloop.IOLoop.current().spawn_callback(self._process_pending_jobs)

    async def _process_pending_jobs(self):
        while True:
            req = await self.pending_requests.get()
            actions = {
                job.ACTION_SRSERVER_REPORT_JOB_STATUS: self._report_job_status,
            }
            response = await actions[req.action](req)
            await _send_to_supervisor(response, req)

    # TODO(e-carlin): See if you get can njsmith's @_rpc_handler annotation working here
    async def _report_job_status(self, req):
        """Get the current status of a specific job in the given run_dir."""
        status = job_supervisor_client.JobStatus.MISSING
        run_dir_jhash, run_dir_status = self._run_dir_status(req.run_dir)
        if run_dir_jhash == req.jhash:
            status = run_dir_status

        return pkcollections.Dict({
            'action': job.ACTION_DRIVER_REPORT_JOB_STATUS,
            'status': status.value,
        }) 

    def _run_dir_status(self, run_dir):
        """Get the current status of whatever's happening in run_dir.

        Returns:
        Tuple of (jhash or None, status of that job)

        """
        disk_in_path = run_dir.join('in.json')
        disk_status_path = run_dir.join('status')
        if disk_in_path.exists() and disk_status_path.exists():
            # status should be recorded on disk XOR in memory
            assert run_dir not in self._report_jobs
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
        elif run_dir in self._report_jobs:
            job_info = self._report_jobs[run_dir]
            return job_info.jhash, job_info.status
            
        return None, job_supervisor_client.JobStatus.MISSING























    # async def run_extract_job(self, io_loop, run_dir, jhash, subcmd, arg):
    #     pkdc('{} {}: {} {}', run_dir, jhash, subcmd, arg)
    #     status = self.report_job_status(run_dir, jhash)
    #     if status is job_supervisor_client.JobStatus.MISSING:
    #         pkdlog('{} {}: report is missing; skipping extract job',
    #                run_dir, jhash)
    #         return {}
    #     # figure out which backend and any backend-specific info
    #     runner_info_file = run_dir.join(_RUNNER_INFO_BASENAME)
    #     if runner_info_file.exists():
    #         runner_info = pkjson.load_any(runner_info_file)
    #     else:
    #         # Legacy run_dir
    #         runner_info = pkcollections.Dict(
    #             version=1, backend='local', backend_info={},
    #         )
    #     assert runner_info.version == 1

    #     # run the job
    #     cmd = ['sirepo', 'extract', subcmd, arg]
    #     result = await local_process.run_extract_job( #TODO(e-carlin): Handle multiple backends
    #        io_loop, run_dir, cmd, runner_info.backend_info,
    #     )

    #     if result.stderr:
    #         pkdlog(
    #             'got output on stderr ({} {}):\n{}',
    #             run_dir, jhash,
    #             result.stderr.decode('utf-8', errors='ignore'),
    #         )

    #     if result.returncode != 0:
    #         pkdlog(
    #             'failed with return code {} ({} {}), stdout:\n{}',
    #             result.returncode,
    #             run_dir,
    #             subcmd,
    #             result.stdout.decode('utf-8', errors='ignore'),
    #         )
    #         raise AssertionError

    #     return pkjson.load_any(result.stdout)


    # async def start_report_job(self, io_loop, run_dir, jhash, backend, cmd, tmp_dir):
    #     assert run_dir not in self.report_jobs
    #     #TODO(robnagler): this has to be atomic.
    #     pkio.unchecked_remove(run_dir)
    #     tmp_dir.rename(run_dir)
    #     report_job = local_process.start_report_job(run_dir, cmd) # TODO(e-carlin): Handle multiple backends
    #     job_info = _JobInfo(
    #         run_dir, jhash, job_supervisor_client.JobStatus.RUNNING, report_job
    #     )
    #     self.report_jobs[run_dir] = job_info

    #     await self._supervise_report_job(io_loop, run_dir, jhash, job_info)
        
    # async def _supervise_report_job(self, io_loop, run_dir, jhash, job_info):
    #     with _catch_and_log_errors(Exception, 'error in _supervise_report_job'):
    #         # Make sure returncode is defined in the finally block, even if
    #         # wait() somehow crashes
    #         returncode = None
    #         try:
    #             returncode = await job_info.report_job.wait_for_exit()
    #         finally:
    #             # Clear up our in-memory status
    #             assert self.report_jobs[run_dir] is job_info
    #             del self.report_jobs[run_dir]
    #             # Write status to disk
    #             if job_info.cancel_requested:
    #                 _write_status(job_supervisor_client.JobStatus.CANCELED, run_dir)
    #                 await self.run_extract_job(
    #                     io_loop, run_dir, jhash, 'remove_last_frame', '[]',
    #                 )
    #             elif returncode == 0:
    #                 _write_status(job_supervisor_client.JobStatus.COMPLETED, run_dir)
    #             else:
    #                 pkdlog(
    #                     '{} {}: job failed, returncode = {}',
    #                     run_dir, jhash, returncode,
    #                 )
    #                 _write_status(job_supervisor_client.JobStatus.ERROR, run_dir)

# class _JobInfo:
#     def __init__(self, run_dir, jhash, status, report_job):
#         self.run_dir = run_dir
#         self.jhash = jhash
#         self.status = status
#         self.report_job = report_job
#         self.cancel_requested = False


# async def _notify_supervisor(data):
#     data.source = 'driver'
#     data.uid = _AGENT_ID 
#     #TODO(e-carlin): This is ugly
#     pkdlog('Notifying supervisor: {}',  {x: data[x] for x in data if x not in ['result', 'arg']})
#     pkdc('Full body: {}', data)

#     http_client = tornado.httpclient.AsyncHTTPClient()
#     response = await http_client.fetch(
#         cfg.supervisor_uri,
#         method='POST',
#         body=pkjson.dump_bytes(data),
#         request_timeout=math.inf,
#         )

#     supervisor_req = pkcollections.Dict(pkjson.load_any(response.body))
#     pkdc('Supervisor responded with: {}', supervisor_req)
#     return supervisor_req


# async def _notify_supervisor_ready_for_work(io_loop, job_tracker):
#     while True:
#         data = pkcollections.Dict({
#             'action': job.ACTION_DRIVER_READY_FOR_WORK,
#         })
#         try:
#             req = await _notify_supervisor(data)
#         except ConnectionRefusedError as e:
#             pkdlog('Connection refused while calling supervisor ready_for_work. \
#                 Sleeping and trying again. Caused by: {}', e)
#             await tornado.gen.sleep(1)    
#             continue
#         if req.action == job.ACTION_SUPERVISOR_KEEP_ALIVE:
#             continue
#         io_loop.spawn_callback(_process_supervisor_request, io_loop, job_tracker, req)


# async def _process_supervisor_request(io_loop, job_tracker, req):
#     #TODO(e-carlin): This code is repetitive.
#     if req.action == job.ACTION_SRSERVER_START_REPORT_JOB:
#         results = await _start_report_job(io_loop, job_tracker, req)
#         await _notify_supervisor(results)
#         return
#     elif req.action == job.ACTION_SRSERVER_REPORT_JOB_STATUS:
#         status = _report_job_status(job_tracker, req)
#         await _notify_supervisor(status)
#         return
#     elif req.action == job.ACTION_SRSERVER_RUN_EXTRACT_JOB:
#         results = await _run_extract_job(io_loop, job_tracker, req)
#         await _notify_supervisor(results)
#         return
#     else:
#         raise Exception(f'Request.action {req.action} unknown')
    

# def _report_job_status(job_tracker, req):
#     pkdc('report_job_status: {}', req)
#     status =  job_tracker.report_job_status(
#         #TODO(e-carlin): Find a common place to do pkio.py_path() these are littered around
#         pkio.py_path(req.run_dir), req.jhash
#     ).value
#     return pkcollections.Dict({
#         'action': job.ACTION_DRIVER_REPORT_JOB_STATUS,
#         'id': req.id,
#         'uid': req.uid,
#         'status': status,
#     })
            

# async def _run_extract_job(io_loop, job_tracker, req):
#     pkdc('run_extrac_job: {}', req)
#     result = await job_tracker.run_extract_job(
#         io_loop,
#         pkio.py_path(req.run_dir),
#         req.jhash,
#         req.subcmd,
#         req.arg,
#     )
#     return pkcollections.Dict({
#         'action' : job.ACTION_DRIVER_EXTRACT_JOB_RESULTS,
#         'id': req.id,
#         'uid': req.uid,
#         'result': result,
#     })


# async def _start_report_job(io_loop, job_tracker, req):
#     pkdc('start_report_job: {}', req)
#     await job_tracker.start_report_job(
#         io_loop,
#         pkio.py_path(req.run_dir), req.jhash,
#         req.backend,
#         req.cmd, pkio.py_path(req.tmp_dir),
#     )
#     return pkcollections.Dict({
#         'action': job.ACTION_DRIVER_REPORT_JOB_STARTED,
#         'id': req.id,
#         'uid': req.uid,
#     })


# def _write_status(status, run_dir):
#     fn = run_dir.join('result.json')
#     if not fn.exists():
#         pkjson.dump_pretty({'state': status.value}, filename=fn)
#         pkio.write_text(run_dir.join('status'), status.value)


# @contextlib.contextmanager
# def _catch_and_log_errors(exc_type, msg, *args, **kwargs):
#     try:
#         yield
#     except exc_type:
#         pkdlog(msg, *args, **kwargs)
#         pkdlog(pkdexc())


# _RUNNER_INFO_BASENAME = 'runner-info.json'

cfg = pkconfig.init(
    supervisor_uri=(job.cfg.supervisor_ws_uri, str, 'the uri to reach the supervisor on')
)