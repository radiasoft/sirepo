# -*- coding: utf-8 -*-
"""The runner daemon.

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from __future__ import absolute_import, division, print_function

import aenum
import async_generator
import collections
import contextlib
import curses
import functools
import os
from pykern.pkdebug import pkdp, pkdc, pkdlog, pkdexc
from pykern import pkcollections
from pykern import pkio
from pykern import pkjson
from sirepo import runner_client
from sirepo import srdb
from sirepo.runner_daemon import local_process, docker_process
import subprocess
import sys
import time
import trio

_CHUNK_SIZE = 4096
_LISTEN_QUEUE = 1000

_KILL_TIMEOUT_SECS = 3

_RUNNER_INFO_BASENAME = 'runner-info.json'

_BACKENDS = {
    'local': local_process,
    'docker': docker_process,
}


@contextlib.contextmanager
def _catch_and_log_errors(exc_type, msg, *args, **kwargs):
    try:
        yield
    except trio.MultiError as multi_exc:
        raise AssertionError('handle MultiErrors in _catch_and_log_errors')
    except exc_type:
        pkdlog(msg, *args, **kwargs)
        pkdlog(pkdexc())


# Used to make sure that if we get simultaneous RPCs for the same jid/run_dir,
# then only one RPC handler runs at a time. Like defaultdict(trio.Lock), but
# without the memory leak. (Maybe should be upstreamed to Trio?)
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


# Cut down version of simulation_db.write_result
def _write_status(status, run_dir):
    fn = run_dir.join('result.json')
    if not fn.exists():
        pkjson.dump_pretty({'state': status.value}, filename=fn)
        pkio.write_text(run_dir.join('status'), status.value)


class _JobInfo:
    def __init__(self, run_dir, jhash, status, report_job):
        self.run_dir = run_dir
        self.jhash = jhash
        self.status = status
        self.report_job = report_job
        self.cancel_requested = False


class _JobTracker:
    def __init__(self, nursery):
        self.report_jobs = {}
        self.locks = _LockDict()
        self._nursery = nursery

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
        else:
            return None, runner_client.JobStatus.MISSING

    def report_job_status(self, run_dir, jhash):
        """Get the current status of a specific job in the given run_dir.

        """
        run_dir_jhash, run_dir_status = self.run_dir_status(run_dir)
        if run_dir_jhash == jhash:
            return run_dir_status
        else:
            return runner_client.JobStatus.MISSING

    async def kill_all(self, run_dir):
        """Forcibly stop any jobs currently running in run_dir.

        Assumes that you've already checked what those jobs are (perhaps by
        calling run_dir_status), and decided they need to die.

        """
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
        report_job = await _BACKENDS[backend].start_report_job(run_dir, cmd)
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

    async def _supervise_report_job(self, run_dir, jhash, job_info):
        with _catch_and_log_errors(Exception, 'error in _supervise_report_job'):
            # Make sure returncode is defined in the finally block, even if
            # wait() somehow crashes
            returncode = None
            try:
                returncode = await job_info.report_job.wait()
            finally:
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

    async def run_extract_job(self, run_dir, jhash, subcmd, arg):
        pkdc('{} {}: {} {}', run_dir, jhash, subcmd, arg)
        status = self.report_job_status(run_dir, jhash)
        if status is runner_client.JobStatus.MISSING:
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
        result = await _BACKENDS[runner_info.backend].run_extract_job(
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


_RPC_HANDLERS = {}


def _rpc_handler(fn):
    _RPC_HANDLERS[fn.__name__.lstrip('_')] = fn
    return fn


@_rpc_handler
async def _start_report_job(job_tracker, request):
    pkdc('start_report_job: {}', request)
    await job_tracker.start_report_job(
        request.run_dir, request.jhash,
        request.backend,
        request.cmd, pkio.py_path(request.tmp_dir),
    )
    return {}


@_rpc_handler
async def _report_job_status(job_tracker, request):
    pkdc('report_job_status: {}', request)
    return {
        'status': job_tracker.report_job_status(request.run_dir, request.jhash).value,
    }


@_rpc_handler
async def _cancel_report_job(job_tracker, request):
    jhash, status = job_tracker.run_dir_status(request.run_dir)
    if jhash == request.jhash:
        await job_tracker.kill_all(request.run_dir)
    return {}


@_rpc_handler
async def _run_extract_job(job_tracker, request):
    return await job_tracker.run_extract_job(
        request.run_dir,
        request.jhash,
        request.subcmd,
        request.arg,
    )


# XX should we just always acquire a per-job lock here, to make sure we never
# have to worry about different requests for the same job racing?
async def _handle_conn(job_tracker, stream):
    with _catch_and_log_errors(Exception, 'error handling request'):
        request_bytes = bytearray()
        while True:
            chunk = await stream.receive_some(_CHUNK_SIZE)
            if not chunk:
                break
            request_bytes += chunk
        request = pkjson.load_any(request_bytes)
        if 'run_dir' in request:
            request.run_dir = pkio.py_path(request.run_dir)
        pkdc('runner request: {!r}', request)
        handler = _RPC_HANDLERS[request.action]
        async with job_tracker.locks[request.run_dir]:
            response = await handler(job_tracker, request)
        pkdc('runner response: {!r}', response)
        response_bytes = pkjson.dump_bytes(response)
        await stream.send_all(response_bytes)


def _remove_old_tmp_dirs():
    pkdlog('scanning for stale tmp dirs')
    count = 0
    cutoff = time.time() - srdb.TMP_DIR_CLEANUP_TIME
    for dirpath, dirnames, filenames in os.walk(srdb.root()):
        if (dirpath.endswith(srdb.TMP_DIR_SUFFIX)
                and os.stat(dirpath).st_mtime < cutoff):
            pkdlog('removing stale tmp dir: {}', dirpath)
            pkio.unchecked_remove(dirpath)
            count += 1
    pkdlog('finished scanning for stale tmp dirs ({} found)', count)


async def _tmp_dir_gc():
    while True:
        with _catch_and_log_errors(Exception, 'error running tmp dir gc'):
            await trio.run_sync_in_worker_thread(_remove_old_tmp_dirs)
            await trio.sleep(srdb.TMP_DIR_CLEANUP_TIME)


async def _main():
    pkdlog('runner daemon starting up')
    with trio.socket.socket(family=trio.socket.AF_UNIX) as sock:
        # XX TODO: better strategy for handoff between runner instances
        # Clear out any stale socket file
        sock_path = srdb.runner_socket_path()
        pkio.unchecked_remove(sock_path)
        await sock.bind(str(sock_path))
        sock.listen(_LISTEN_QUEUE)
        listener = trio.SocketListener(sock)

        async with trio.open_nursery() as nursery:
            nursery.start_soon(_tmp_dir_gc)
            job_tracker = _JobTracker(nursery)
            await trio.serve_listeners(
                functools.partial(_handle_conn, job_tracker),
                [listener],
            )


def start():
    """Starts the runner daemon."""
    trio.run(_main)


# Temporary (?) hack to make testing easier: starts up the http dev server
# under py2 and the runner daemon under py3, and if either exits then kills
# the other.
_RUNNER_DAEMON_OUTPUT_COLOR = 2  # green
_FLASK_DEV_OUTPUT_COLOR = 4  # blue

def _color(num):
    colors = curses.tigetstr('setaf')
    if colors is None:
        return b''
    return curses.tparm(colors, num)


async def _run_cmd(color, cmd, **kwargs):
    async def forward_to_stdout_with_color(stream):
        while True:
            data = await stream.receive_some(_CHUNK_SIZE)
            if not data:
                return
            sys.stdout.buffer.raw.write(_color(color) + data + _color(0))

    kwargs['stdin'] = subprocess.DEVNULL
    kwargs['stdout'] = subprocess.PIPE
    kwargs['stderr'] = subprocess.STDOUT
    async with trio.open_nursery() as nursery:
        async with trio.Process(cmd, **kwargs) as process:
            nursery.start_soon(forward_to_stdout_with_color, process.stdout)
            await process.wait()


async def _dev_main():
    curses.setupterm()

    # To be inherited by children
    os.environ['SIREPO_FEATURE_CONFIG_RUNNER_DAEMON'] = '1'
    os.environ['PYTHONUNBUFFERED'] = '1'

    async with trio.open_nursery() as nursery:
        async def _run_cmd_in_env_then_quit(py_env_name, color, cmd):
            env = {**os.environ, 'PYENV_VERSION': py_env_name}
            await _run_cmd(color, ['pyenv', 'exec'] + cmd, env=env)
            nursery.cancel_scope.cancel()

        nursery.start_soon(
            _run_cmd_in_env_then_quit,
            'py2', _FLASK_DEV_OUTPUT_COLOR, ['sirepo', 'service', 'http'],
        )
        # We could just run _main here, but spawning a subprocess makes sure
        # that everyone has the same config, e.g. for
        # SIREPO_FEATURE_FLAG_RUNNER_DAEMON
        nursery.start_soon(
            _run_cmd_in_env_then_quit,
            'py3', _RUNNER_DAEMON_OUTPUT_COLOR, ['sirepo', 'runner', 'start'],
        )


def dev():
    """Starts the runner daemon + the HTTP dev server."""
    trio.run(_dev_main)
