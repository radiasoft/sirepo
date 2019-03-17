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
from pykern import pkio
from pykern import pkjson
from sirepo import runner_client
from sirepo import srdb
from sirepo.runner_daemon import local_process, docker_process
import subprocess
import sys
import time
import trio

# Every _TMP_DIR_CLEANUP_TIME seconds, we scan through the run database, and
# any directories that are named '*.tmp', and whose mtime is
# >_TMP_DIR_CLEANUP_TIME in the past, are deleted.
_TMP_DIR_CLEANUP_TIME = 24 * 60 * 60  # 24 hours

_CHUNK_SIZE = 4096
_LISTEN_QUEUE = 1000

_KILL_TIMEOUT_SECS = 3


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
            await self._waiters[keys].park()
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
    def __init__(self, run_dir, jhash, status, process):
        self.run_dir = run_dir
        self.jhash = jhash
        self.status = status
        self.process = process
        self.cancel_requested = False


class _JobTracker:
    def __init__(self, nursery):
        self.jobs = {}
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
            assert run_dir not in self.jobs
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
        elif run_dir in self.jobs:
            job_info = self.jobs[run_dir]
            return job_info.jhash, job_info.status
        else:
            return None, runner_client.JobStatus.MISSING

    def job_status(self, run_dir, jhash):
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
        job_info = self.jobs.get(run_dir)
        if job_info is None:
            return
        if job_info.status is not runner_client.JobStatus.RUNNING:
            return
        pkdlog(
            'kill_all {}: killing job with jhash {}',
            run_dir, job_info.jhash,
        )
        job_info.cancel_requested = True
        await job_info.process.kill(_KILL_TIMEOUT_SECS)

    async def start_job(self, run_dir, jhash, cmd, tmp_dir):
        # First make sure there's no-one else using the run_dir
        current_jhash, current_status = self.run_dir_status(run_dir)
        if current_status is runner_client.JobStatus.RUNNING:
            # Something's running.
            if current_jhash == jhash:
                # It's already the requested job, so we have nothing to
                # do. Throw away the tmp_dir and move on.
                pkdlog(
                    'start_job {} {}: job is already running; skipping',
                    run_dir, jhash
                )
                pkio.unchecked_remove(tmp_dir)
                return
            else:
                # It's some other job. Better kill it before doing
                # anything else.
                # XX TODO: should we check some kind of sequence number
                # here? I don't know how those work.
                pkdlog(
                    'start_job {} {}: stale job is still running; killing it',
                    run_dir, jhash
                )
                await self.kill_all(run_dir)

        # Okay, now we have the dir to ourselves. Set up the new run_dir:
        assert run_dir not in self.jobs
        pkio.unchecked_remove(run_dir)
        tmp_dir.rename(run_dir)
        # Start the job:
        process = await local_process.start(run_dir, cmd)
        # And update our records so we know it's running:
        job_info = _JobInfo(
            run_dir, jhash, runner_client.JobStatus.RUNNING, process
        )
        self.jobs[run_dir] = job_info

        # And finally, start a background task to watch over it.
        self._nursery.start_soon(self._supervise_job, run_dir, jhash, job_info)

    async def _supervise_job(self, run_dir, jhash, job_info):
        with _catch_and_log_errors(Exception, 'error in _supervise_job'):
            try:
                returncode = await job_info.process.wait()

                if job_info.cancel_requested:
                    _write_status(runner_client.JobStatus.CANCELED, run_dir)
                elif returncode:
                    pkdlog(
                        '{} {}: job failed, returncode = {}',
                        run_dir, jhash, returncode,
                    )
                    _write_status(runner_client.JobStatus.ERROR, run_dir)
                else:
                    _write_status(runner_client.JobStatus.COMPLETED, run_dir)
            finally:
                # job should be dead by now, but let's make sure
                await job_info.process.kill(_KILL_TIMEOUT_SECS)
                assert self.jobs[run_dir] is job_info
                del self.jobs[run_dir]


_RPC_HANDLERS = {}


def _rpc_handler(fn):
    _RPC_HANDLERS[fn.__name__.lstrip('_')] = fn
    return fn


@_rpc_handler
async def _start_job(job_tracker, request):
    pkdc('start_job: {}', request)
    await job_tracker.start_job(
        request.run_dir, request.jhash, request.cmd,
        pkio.py_path(request.tmp_dir),
    )
    return {}


@_rpc_handler
async def _job_status(job_tracker, request):
    pkdc('job_status: {}', request)
    return {
        'status': job_tracker.job_status(request.run_dir, request.jhash).value
    }


@_rpc_handler
async def _cancel_job(job_tracker, request):
    run_dir_jhash, run_dir_status = job_tracker.run_dir_status(request.run_dir)
    if run_dir_jhash != request.jhash:
        return {}
    await job_tracker.kill_all(request.run_dir)
    return {}


# XX should we just always acquire a per-job lock here, to make sure we never
# have to worry about different requests for the same job racing?
async def _handle_conn(job_tracker, lock_dict, stream):
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
        pkdlog('runner request: {!r}', request)
        handler = _RPC_HANDLERS[request.action]
        async with lock_dict[request.run_dir]:
            response = await handler(job_tracker, request)
        pkdlog('runner response: {!r}', response)
        response_bytes = pkjson.dump_bytes(response)
        await stream.send_all(response_bytes)


def _remove_old_tmp_dirs():
    pkdlog('scanning for stale tmp dirs')
    count = 0
    cutoff = time.time() - _TMP_DIR_CLEANUP_TIME
    for dirpath, dirnames, filenames in os.walk(srdb.root()):
        if (dirpath.endswith('.tmp')
                and os.stat(dirpath).st_mtime < cutoff):
            pkdlog('removing stale tmp dir: {}', dirpath)
            pkio.unchecked_remove(dirpath)
            count += 1
    pkdlog('finished scanning for stale tmp dirs ({} found)', count)


async def _tmp_dir_gc():
    while True:
        with _catch_and_log_errors(Exception, 'error running tmp dir gc'):
            await trio.run_sync_in_worker_thread(_remove_old_tmp_dirs)
            await trio.sleep(_TMP_DIR_CLEANUP_TIME)


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
            lock_dict = _LockDict()
            await trio.serve_listeners(
                functools.partial(_handle_conn, job_tracker, lock_dict),
                [listener]
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
