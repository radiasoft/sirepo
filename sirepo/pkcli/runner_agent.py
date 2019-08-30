# -*- coding: utf-8 -*-
"""The runner daemon.

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function

import asks
import async_generator
from pykern import pkio
from pykern import pkjson
from pykern import pkcollections
from pykern.pkdebug import pkdp
from sirepo import runner_client
from sirepo import runner_daemon
import trio

ACTION_READY_FOR_WORK = 'ready_for_work'
ACTION_PROCESS_RESULT = 'process_result'


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

async def _call_daemon_ready_for_work():
    body = {
        'action': 'ready_for_work',
        'data': {},
    }
    return await _call_daemon(body)

async def _call_daemon_with_result(result):
    body = {
        'action': 'process_result',
        'data': result,
    }
    await _call_daemon(body) # TODO(e-carlin): Do nothing with response from this call?

async def _main():
    async with trio.open_nursery() as nursery:
        job_tracker = _JobTracker(nursery)
        while True: # TODO(e-carlin): there has to be something more clever than this
            request = await _call_daemon_ready_for_work()
            action = request.get('action', 'no_op') # TODO(e-carlin): Defaulting to no-op isn't right
            action_types = {
                'no_op': _perform_no_op,
                'start_report_job': _start_report_job,
            }

            await action_types[action](job_tracker, request)

async def _perform_no_op(job_tracker, request):
    pkdp('Daemon requested no_op. Going to sleep for a bit.')
    await trio.sleep(2) # TODO(e-carlin): Exponential backoff?

async def _start_report_job(job_tracker, request):
    pkdp(f'Daemon requested start_report_job: {request}')

    async with job_tracker.locks[request.run_dir]:
        await job_tracker.start_report_job(
            request.run_dir, request.jhash,
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
class _LockDict:
    def __init__(self):
        # {key: ParkingLot}
        # lock is held iff the key exists
        self._waiters = {}

    @async_generator.asynccontextmanager
    async def __getitem__(self, key):
        # acquire
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

    async def start_report_job(self, run_dir, jhash, backend, cmd, tmp_dir):
        pkdp(f'&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&& {backend}')
        import os
        import re
        _EXEC_ENV_REMOVE = re.compile('^(OMPI_|PMIX_|SIREPO_|PYKERN_)')
        env = dict(os.environ)
        for k in list(env):
            if _EXEC_ENV_REMOVE.search(k):
                del env[k]
        # env['SIREPO_MPI_CORES'] = str(mpi.cfg.cores)


        env['PYENV_VERSION'] = 'py2'
        cmd = ['pyenv', 'exec'] + cmd
        # TODO(e-carlin): Actually handle the tmp vs run dir. See start_report_job()
        # in pkcli/runner.py
        ###
        pkio.unchecked_remove(run_dir)
        tmp_dir = pkio.py_path(tmp_dir)
        tmp_dir.rename(run_dir)
        ####
        cmd = ['python', 'long_run.py']
        p = await trio.open_process(
            cmd,
            cwd='/home/vagrant/src/radiasoft/sirepo/sirepo/pkcli'
            # cwd=run_dir,
            # env=env
        )
        pkdp(f'Report job started')
        report_job = _LocalReportJob(p, {'pid': p.pid})
        job_info = _JobInfo(
            run_dir, jhash, runner_client.JobStatus.RUNNING, report_job
        )
        self.report_jobs[run_dir] = job_info
        async def _supervise_job(run_dir, jhash, job_info):
            pkdp(f'Starting to wait on jhash {jhash}')
            returncode = await job_info.report_job.wait()
            pkdp(f'jhash {jhash} finished with exit code {returncode}')

        self._nursery.start_soon(
            _supervise_job, run_dir, jhash, job_info
        )
        """
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
            else:
                # It's some other job. Better kill it before doing
                # anything else.
                # XX TODO: should we check some kind of sequence number
                # here? I don't know how those work.
                pkdlog(
                    'stale job is still running; killing it (run_dir={}, jhash={})',
                    run_dir, jhash,
                )
                await self.kill_all(run_dir)

        # Okay, now we have the dir to ourselves. Set up the new run_dir:
        assert run_dir not in self.report_jobs
        pkio.unchecked_remove(run_dir)
        tmp_dir.rename(run_dir)
        # Start the job:
        # report_job = await _BACKENDS[backend].start_report_job(run_dir, cmd)
        # And update our records so we know it's running:
        job_info = _JobInfo(
            run_dir, jhash, runner_client.JobStatus.RUNNING, report_job,
        )
        self.report_jobs[run_dir] = job_info
        pkjson.dump_pretty(
            {
                'version': 1,
                'backend': backend,
                'backend_info': report_job.backend_info,
            },
            filename=run_dir.join(_RUNNER_INFO_BASENAME),
        )

        # And finally, start a background task to watch over it.
        self._nursery.start_soon(
            self._supervise_report_job, run_dir, jhash, job_info,
        )
        """



class _LocalReportJob:
    def __init__(self, trio_process, backend_info):
        self._trio_process = trio_process
        self.backend_info = backend_info

    async def kill(self, grace_period):
        # Everything here is a no-op if the process is already dead
        self._trio_process.terminate()
        with trio.move_on_after(grace_period):
            await self._trio_process.wait()
        self._trio_process.kill()
        await self._trio_process.wait()

    async def wait(self):
        await self._trio_process.wait()
        return self._trio_process.returncode