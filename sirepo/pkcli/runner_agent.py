# -*- coding: utf-8 -*-
"""The runner daemon.

#TODO(robnagler): Naming thoughts...

    I think we should use "job_supervisor" for the runner_daemon.

    "job_driver" for runner_agent (others: controller, director, overseer, proxy)
    The use of driver is is a bit of a stretch so proxy or controller might work, too, but
    I tend to think of a supervisor as an operating system level thing, and device driver as
    the low level thing that controls a particular device.

    An driver has a class (Subprocess, Docker, NERSC). An driver has a user and
    it is reusable, but it should only be responsible for one job at a time. For NERSC,
    we'll have multiple drivers reporting in if the user starts multiple jobs. It will
    be simpler that way, and the supervisor handles all resource management that way.
    There will be significant logic around this, and rather that the driver's
    responsibility is just the running of a job.

    I also think server.py is too generic. It's a broker. That will help us keep things
    in the right mindset. It shouldn't do any work, just exchange messages with the
    other services (supervisor, GUI, etc.).

    I think we should remove "runner", because it is verb on an unknown object.

    A "job" has a user, type, number of cores, node, etc. The
    supervisor will decide if/when/where it should run based on the job
    characteristics. We speak about a job as the instance running, which
    has more characteristics, than the job before it is running. We ask
    for watchPointReport1 for simulation X, and it is a single job that
    could be running. If it is running, it has to have the same parameters (jhash)
    or it should be killed, and started with the correct parameters. I think
    the use of "job" is fine.

    There is also job output. run_dir doesn't really describe it clearly. A job
    runs in a directory which has inputs and outputs. The output may be used by
    another job, and therefore it is a prerequisite for the other job.

    I've sprinkled the terms in my comments below

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
#TODO(robnagler): sorting lines simply alphabetically makes for easier maintenance.
#   In emacs, there's a sort-lines. In vim, you can select region and pipe to "sort".
#   I suspect in VSCode there's something similar. This puts all the from's before
#   import's but that shouldn't matter; a more complex algorithm (looking for module
#   names) requires too much work, and doesn't give us anything.
from pykern import pkcollections
from pykern import pkio
from pykern import pkjson
from pykern.pkdebug import pkdp, pkdlog
from sirepo import runner_client
from sirepo import runner_daemon
from sirepo.runner_daemon import local_process
import asks
import async_generator
import trio

ACTION_READY_FOR_WORK = 'ready_for_work'
ACTION_PROCESS_RESULT = 'process_result'


_KILL_TIMEOUT_SECS = 3

def start():
    trio.run(_main)


async def _call_daemon(body):
    try:
        response = await asks.post('http://localhost:8080', json=body)
        pkdp(f'Dameon responded with: {response.content}')
        return pkcollections.Dict(pkjson.load_any(response.content))
        # return pkjson.load_any(response.content)
    except Exception as e:
        pkdp(f'Exception with _call_daemon(). Caused by: {e}')
        return {}


#TODO(robnagler): these two wrappers seem unecessary. I also think it could be active:
#    rather _notify(READY_FOR_WORK)
#    and _notify(PROCESS_RESULT, result)
# Note that PROCESS_RESULT is a demand on the supervisor, rather, you want to
#    _notify(JOB_FINISHED, status)
# "Result" implies a calculation, but we should keep the "status" parlance. The job
# may have crashed (error) or succeed (completed).
async def _call_daemon_ready_for_work():
    body = {
#TODO(robnagler): use ACTION_READY_FOR_WORK
        'action': 'ready_for_work',
        'data': {},
    }
    return await _call_daemon(body)


async def _call_daemon_with_result(result):
    body = {
#TODO(robnagler): use ACTION_PROCESS_RESULT
        'action': 'process_result',
        'data': result,
    }
    await _call_daemon(body) # TODO(e-carlin): Do nothing with response from this call?

async def _main():
    async with trio.open_nursery() as nursery:
        job_tracker = _JobTracker(nursery)
        while True: # TODO(e-carlin): there has to be something more clever than this
            request = await _call_daemon_ready_for_work()
#TODO(robnagler): no_op is not correct. The driver's job is to either be doing something
#   or asking the supervisor for more work. There is no "no_op" on the driver's side of things
#   The supervisor will be waiting for work from the broker (server.py) or notifications from the
#   driver. If there is no response or the request fails for a timeout or connection failure,
#   it simply resends the last notification that was queued up. It might have been lost.
#   Notications should be idempotent.
            action = request.get('action', 'no_op') # TODO(e-carlin): Defaulting to no-op isn't right
            action_types = {
                'no_op': _perform_no_op,
                'start_report_job': _start_report_job,
                'report_job_status': _report_job_status,
            }

            await action_types[action](job_tracker, request)

async def _perform_no_op(job_tracker, request):
    pkdp('Daemon requested no_op. Going to sleep for a bit.')
    await trio.sleep(2) # TODO(e-carlin): Exponential backoff?

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
#TODO(robnagler): else: is unnecessary so remove it for less code and clearer flow
        else:
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
#TODO(robnagler): else: is unnecessary so remove it for less code and clearer flow
        else:
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
#TODO(robnagler): else: is unnecessary so remove it for less code and clearer flow
            else:
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
#TODO(robnagler) not a useful comment
        # Start the job:
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
