# -*- coding: utf-8 -*-
"""The runner daemon.

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function

from pykern import pkcollections, pkio, pkjson
from pykern.pkdebug import pkdlog, pkdp, pkdexc
from sirepo import runner_client, runner_daemon
from sirepo.runner_daemon import local_process
import asks
import async_generator
import trio

ACTION_READY_FOR_WORK = 'ready_for_work'
ACTION_PROCESS_RESULT = 'process_result'


_KILL_TIMEOUT_SECS = 3

def start():
    trio.run(_main)


async def _notify_supervisor(action, data={}):
    try:
        body = {
            'source': 'driver',
            'driver_id': 'sVKP0jmq', #TODO(e-carlin): Make real id
            'action': action,
            'data': data
        }
        pkdp(f'calling notify with body {body}')
        response = await asks.post('http://localhost:8080', json=body)
        pkdp(f'Dameon responded with: {response}')
        return pkcollections.Dict(pkjson.load_any(response.content))
        # return pkjson.load_any(response.content)
    except Exception as e:
        pkdp(f'Exception with _call_daemon(). Caused by: {e}')
        return {}


async def _main():
    async with trio.open_nursery() as nursery:
        job_tracker = _JobTracker(nursery)
        while True: # TODO(e-carlin): there has to be something more clever than this
            try:
                request = await _notify_supervisor(ACTION_READY_FOR_WORK)
                action = request['action']
                action_types = {
                    'keep_alive': _perform_keep_alive,
                    'start_report_job': _start_report_job,
                    'report_job_status': _report_job_status,
                }

                await action_types[action](job_tracker, request)
            except Exception as e:
                pkdlog(f'Exception with request response with supervisor. Caused by: {e}')
                pkdexc()
                await trio.sleep(2) #TODO(e-carlin): Delete in favor of long polling

async def _perform_keep_alive(job_tracker, request):
    pkdp('Daemon requested keep_alive. Requesting again')
    await trio.sleep(2) #TODO(e-carlin): Delete in favor of long polling

async def _report_job_status(job_tracker, request):
    pkdp(f'Daemon requested repot_job_status: {request}')
    # TODO(e-carlin): this "async with" is the same as in _start_report_job. Need to abstract
#TODO(robnagler) this lock should be encapsulated inside JobTracker. I don't think
#   job_status needs a lock anyway.
    async with job_tracker.locks[request.run_dir]:
        # TODO(e-carlin): report_job_status() isn't async. That means it has a
        # different interface than the other operations. Need abstraction that
        # can handle this
        #TODO(robnagler): none of the work the main driver Task does should await.
        #     Rather it should do something atomically, and report it back, or start
        #     another Task to do a potentially blocking task such as starting a job.
        await job_tracker.report_job_status()

async def _start_report_job(job_tracker, request):
    pkdp(f'Daemon requested start_report_job: {request}')

#TODO(robnagler) this lock should be encapsulated inside JobTracker
    async with job_tracker.locks[request.run_dir]:
        await job_tracker.start_report_job(
            pkio.py_path(request.run_dir), request.jhash,
            request.backend,
            request.cmd, pkio.py_path(request.tmp_dir),
        )
        return {}


class _JobInfo:
    def __init__(self, run_dir, jhash, status, report_job):
        self.run_dir = run_dir
        self.jhash = jhash
        self.status = status
        self.report_job = report_job
        self.cancel_requested = False

# TODO(e-carlin): Understand what this actually does and why it is useful
# TODO(robnagler): This is a mutex for an object which might not exist ("run_dir").
#    Only one Task can access run_dir at a time, but we don't know run_dir exists
#    until the first request.
#
#    I would probably use trio.Lock instead of hazmat.ParkingLot (see below). It might
#    be faster to do it this way, but we really don't have a speed problem with this
#    particular code so better to use published abstractions.
#
#    We need the logic managing the run_dir existence or not, which trio doesn't handle
#    although you would think it would be a common case. You want to serialize on an
#    object (as opposed to a global lock as we do in simulation_db) to reduce contention.
#
#    This should be in srtrio or somesuch that allows us to share this with
#    runner_daemon, which will surely need this.
class _LockDict:
    def __init__(self):
        # {key: ParkingLot}
        # lock is held iff the key exists
        self._waiters = {}

    #TODO(robnagler): i wonder if this needs to be an async_generator but
    #   i don't understand this well enough.
    @async_generator.asynccontextmanager
    async def __getitem__(self, key):
        #TODO(robnagler): I think it would be cleaner if it looked like:
        #    if key not in self._waiters:
        #        self._waiters[key] = trio.Lock()
        #    a = False
        #    try:
        #        await self._waiters[key].acquire()
        #        a = True
        #        yield
        #    finally:
        #        if a:
        #            ### release_if_owner would make this simpler or
        #            ### at least current_task_is_owner?
        #            self._waiters[key].release()
        #            if not self._waiters[key].locked()
        #                del self._waiters[key]

        #TODO(robnagler) this works because self._waiters read/write is
        #    atomic in a task (no awaits between read ("in") and write ("=")
        #    and read ("park").
        if key not in self._waiters:
            # lock is unheld; adding a key makes it held
            self._waiters[key] = trio.hazmat.ParkingLot()
        else:
            # lock is held; wait for someone to pass it to us
            await self._waiters[key].park()
        try:
            yield
        finally:
            # release
            if self._waiters[key]:
                # someone is waiting, so pass them the lock
                self._waiters[key].unpark()
            else:
                # no-one is waiting, so mark the lock unheld
                del self._waiters[key]

class _JobTracker:
    def __init__(self, nursery):
        self.report_jobs = {}
        self.locks = _LockDict()
        self._nursery = nursery

    async def kill_all(self, run_dir):
#TODO(robnagler): We should definitely avoid the situation of more than one job
#    running in a single run_dir. I don't think this should be "jobs" (next line)
        """Forcibly stop any jobs currently running in run_dir.

        Assumes that you've already checked what those jobs are (perhaps by
        calling run_dir_status), and decided they need to die.
        """
        #TODO(robnagler): report_jobs is similar to lock
        job_info = self.report_jobs.get(run_dir)
        if job_info is None:
            return
        if job_info.status is not runner_client.JobStatus.RUNNING:
            return
        pkdlog(
            'kill_all: killing job with jhash {} in {}',
            job_info.jhash, run_dir,
        )
        job_info.cancel_requested = True
        await job_info.report_job.kill(_KILL_TIMEOUT_SECS)

    def report_job_status(self, run_dir, jhash):
        """Get the current status of a specific job in the given run_dir.

        """
        run_dir_jhash, run_dir_status = self.run_dir_status(run_dir)
        if run_dir_jhash == jhash:
            return run_dir_status

        return runner_client.JobStatus.MISSING

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
        report_job = await local_process.start_report_job(run_dir, cmd) # TODO(e-carlin): Handle multiple backends
        job_info = _JobInfo(
            run_dir, jhash, runner_client.JobStatus.RUNNING, report_job
        )
        self.report_jobs[run_dir] = job_info

        # TODO(e-carlin): Real supervision is needed
        async def _supervise_job(run_dir, jhash, job_info):
            pkdp(f'Starting to wait on jhash {jhash}')
            returncode = await job_info.report_job.wait()
            pkdp(f'jhash {jhash} finished with exit code {returncode}')

        self._nursery.start_soon(
            _supervise_job, run_dir, jhash, job_info
        )
