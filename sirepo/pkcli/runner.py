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
import re
import shlex
from sirepo import mpi
from sirepo import runner_client
from sirepo import srdb
from sirepo.template import template_common
import subprocess
import sys
import trio

# How often threaded blocking operations should wake up and check for Trio
# cancellation
_CANCEL_POLL_INTERVAL = 1

_CHUNK_SIZE = 4096
_LISTEN_QUEUE = 1000

_KILL_TIMEOUT_SECS = 3
#: Need to remove $OMPI and $PMIX to prevent PMIX ERROR:
# See https://github.com/radiasoft/sirepo/issues/1323
# We also remove SIREPO_ and PYKERN vars, because we shouldn't
# need to pass any of that on, just like runner.docker, doesn't
_EXEC_ENV_REMOVE = re.compile('^(OMPI_|PMIX_|SIREPO_|PYKERN_)')


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


# Helper to call container.wait in a async/cancellation-friendly way
async def _container_wait(container):
    while True:
        try:
            return await trio.run_sync_in_worker_thread(
                functools.partial(container.wait, timeout=_CANCEL_POLL_INTERVAL)
            )
        # ReadTimeout is what the documentation says this raises.
        # ConnectionError is what it actually raises.
        # We'll catch both just to be safe.
        except (requests.exceptions.ReadTimeout, requests.exceptions.ConnectionError):
            pass


# Cut down version of simulation_db.write_result
def _write_status(status, run_dir):
    fn = run_dir.join('result.json')
    if not fn.exists():
        pkjson.dump_pretty({'state': status.value}, filename=fn)
        pkio.write_text(run_dir.join('status'), status.value)


def _subprocess_env():
    env = dict(os.environ)
    for k in list(env):
        if _EXEC_ENV_REMOVE.search(k):
            del env[k]
    env['SIREPO_MPI_CORES'] = str(mpi.cfg.cores)
    return env


class _JobInfo:
    def __init__(self, run_dir, jhash, status, process):
        self.run_dir = run_dir
        self.jhash = jhash
        self.status = status
        self.finished = trio.Event()
        self.process = process


class _JobTracker:
    def __init__(self, nursery):
        # XX TODO: eventually we'll need a way to stop this growing without
        # bound, perhaps by clarifying the split in responsibilities between
        # the on-disk simulation_db versus the in-memory status.
        self.jobs = {}
        self._nursery = nursery

    def status(self, run_dir, jhash):
        disk_in_path = run_dir.join('in.json')
        disk_status_path = run_dir.join('status')
        if disk_in_path.exists() and disk_status_path.exists():
            disk_in_text = pkio.read_text(disk_in_path)
            disk_jhash = pkjson.load_any(disk_in_text).reportParametersHash
            if disk_jhash == jhash:
                disk_status = pkio.read_text(disk_status_path)
                if disk_status == 'pending':
                    # We never write this, so it must be stale, in which case
                    # the job is no longer pending...
                    pkdlog(
                        'found "pending" status, treating as "error" ({})',
                        disk_status_path,
                    )
                    return runner_client.JobStatus.ERROR
                return runner_client.JobStatus(disk_status)
        if run_dir in self.jobs and self.jobs[run_dir].jhash == jhash:
            return self.jobs[run_dir].status
        return runner_client.JobStatus.MISSING

    async def start_job(self, run_dir, jhash, cmd):
        await self._nursery.start(self._run_job, run_dir, jhash, cmd)

    async def _run_job(
            self, run_dir, jhash, cmd, *, task_status=trio.TASK_STATUS_IGNORED
    ):
        # XX TODO: there are still some awkward race conditions here if a new
        # job tries to start using the directory while another job is still
        # using it. probably start_job should detect this, and either kill the
        # existing job (if it has a different jhash + older serial), do
        # nothing and report success (if the existing job has the same jhash),
        # or error out (if the existing job has a different jhash + newer
        # serial).
        with _catch_and_log_errors(Exception, 'error in run_job'):
            if run_dir in self.jobs:
                # Right now, I don't know what happens if we reach here while
                # the previous job is still running. The old job might be
                # writing to the new job's freshly-initialized run_dir? This
                # will be fixed once we move away from having server.py write
                # directly into the run_dir.
                pkdlog(
                    'start_job {}: job is already running. old jhash {}, new jhash {}',
                    jhash, self.jobs[run_dir].jhash
                )
                assert self.jobs[run_dir].jhash == jhash
                return
            try:
                env = _subprocess_env()
                run_log_path = run_dir.join(template_common.RUN_LOG)
                # we're in py3 mode, and regular subprocesses will inherit our
                # environment, so we have to manually switch back to py2 mode.
                env['PYENV_VERSION'] = 'py2'
                cmd = ['pyenv', 'exec'] + cmd
                with open(run_log_path, 'a+b') as run_log:
                    process = trio.Process(
                        cmd,
                        cwd=run_dir,
                        start_new_session=True,
                        stdin=subprocess.DEVNULL,
                        stdout=run_log,
                        stderr=run_log,
                        env=env,
                    )
                self.jobs[run_dir] = _JobInfo(
                    run_dir, jhash, runner_client.JobStatus.RUNNING, process
                )
                async with process:
                    task_status.started()
                    # XX more race conditions here, in case we're writing to
                    # the wrong version of the directory...
                    await process.wait()
                    if process.returncode:
                        pkdlog(
                            '{} {}: job failed, returncode = {}',
                            run_dir, jhash, process.returncode,
                        )
                        _write_status(runner_client.JobStatus.ERROR, run_dir)
                    else:
                        _write_status(runner_client.JobStatus.COMPLETED, run_dir)
            finally:
                # _write_status is a no-op if there's already a status, so
                # this really means "if we get here without having written a
                # status, assume there was some error"
                _write_status(runner_client.JobStatus.ERROR, run_dir)
                # Make sure that we clear out the running job info and tell
                # everyone the job is done, no matter what happened
                job_info = self.jobs.pop(run_dir, None)
                if job_info is not None:
                    job_info.finished.set()


_RPC_HANDLERS = {}


def _rpc_handler(fn):
    _RPC_HANDLERS[fn.__name__.lstrip('_')] = fn
    return fn


@_rpc_handler
async def _start_job(job_tracker, request):
    pkdc('start_job: {}', request)
    await job_tracker.start_job(
        request.run_dir, request.jhash, request.cmd
    )
    return {}


@_rpc_handler
async def _job_status(job_tracker, request):
    pkdc('job_status: {}', request)
    return {
        'status': job_tracker.status(request.run_dir, request.jhash).value
    }


@_rpc_handler
async def _cancel_job(job_tracker, request):
    if request.run_dir not in job_tracker.jobs:
        return {}
    job_info = job_tracker.jobs[request.run_dir]
    if job_info.status is not runner_client.JobStatus.RUNNING:
        return {}
    job_info.status = runner_client.JobStatus.CANCELED
    _write_status(runner_client.JobStatus.CANCELED, request.run_dir)
    job_info.process.terminate()
    with trio.move_on_after(_KILL_TIMEOUT_SECS):
        await job_info.finished.wait()
    if job_info.returncode is None:
        job_info.process.kill()
        await job_info.finished.wait()
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
