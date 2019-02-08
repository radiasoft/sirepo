# -*- coding: utf-8 -*-
"""The runner daemon.

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from __future__ import absolute_import, division, print_function

import aenum
import collections
import contextlib
import docker
import functools
from pykern.pkdebug import pkdp, pkdc, pkdlog, pkdexc
from pykern import pkio
from pykern import pkjson
import shlex
from sirepo import mpi
from sirepo import srdb
from sirepo.template import template_common
import trio

# How often threaded blocking operations should wake up and check for Trio
# cancellation
_CANCEL_POLL_INTERVAL = 1

# Global connection pool (don't worry, it doesn't actually make any
# connections until we start using it)
_DOCKER = docker.from_env()

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
        pkjson.dump_pretty({'state': status}, filename=fn)
        pkio.write_text(run_dir.join('status'), status)


def _subprocess_env():
    env = dict(os.environ)
    for k in list(env.items()):
        if _EXEC_ENV_REMOVE.search(k):
            del env[k]
    env['SIREPO_MPI_CORES'] = mpi.cfg.cores
    return env


class _JobStatus(aenum.Enum):
    MISSING = 'missing'   # no data on disk, not currently running
    PENDING = 'pending'   # data on disk is incomplete but it's running
    ERROR = 'error'       # data on disk exists, but job failed somehow
    CANCELED = 'canceled' # data on disk exists, but is incomplete
    COMPLETE = 'complete' # data on disk exists, and is fully usable


class _JobInfo:
    def __init__(self, jid, run_dir, status, process):
        self.jid = jid
        self.status = status
        self.run_dir = run_dir
        self.finished = trio.Event()
        self.process = process


class _JobTracker:
    def __init__(self, nursery):
        # XX TODO: eventually we'll need a way to stop this growing without
        # bound, perhaps by clarifying the split in responsibilities between
        # the on-disk simulation_db versus the in-memory status.
        self.jobs = {}
        self._nursery = nursery

    def status(self, jid, run_dir):
        fn = run_dir.join('status')
        if fn.exists():
            return pkio.read_text(fn)
        if jid in self.jobs:
            return self.jobs[jid].status
        return _JobStatus.MISSING

    async def start_job(self, jid, run_dir, config):
        await self._nursery.start(self._run_job, jid, run_dir, config)

    async def _run_job(
            self, jid, run_dir, config, *, task_status=trio.TASK_STATUS_IGNORED
    ):
        # XX TODO: there are all kinds of race conditions here, e.g. if the
        # same jid gets started multiple times in parallel... we need to
        # revisit this once jids are globally unique, and possibly add
        # features like "if there is another job running with the same
        # user/sim/job but a different hash, then auto-cancel that other job"
        with _catch_and_log_errors(Exception):
            if self.status(jid, run_dir) is not _JobStatus.MISSING:
                return
            try:
                env = _subprocess_env()
                with open(run_dir / template_common.RUN_LOG, 'a+b') as run_log:
                    process = trio.Process(
                        config['command'],
                        cwd=config['working_dir'],
                        start_new_session=True,
                        stdin=run_log,  # XX TODO: should be /dev/null?
                        stdout=run_log,
                        stderr=run_log,
                        env=env,
                    )
                self.jobs[jid] = _JobInfo(
                    jid, run_dir, _JobStatus.PENDING, process
                )
                async with process:
                    task_status.started()
                    await process.wait()
                    if process.returncode:
                        _write_status(_JobStatus.ERROR, run_dir)
                    else:
                        _write_status(_JobStatus.COMPLETE, run_dir)
            finally:
                # _write_status is a no-op if there's already a status, so
                # this really means "if we get here without having written a
                # status, assume there was some error"
                _write_status(_JobStatus.ERROR, run_dir)
                # Make sure that we clear out the running job info and tell
                # everyone the job is done, no matter what happened
                job_info = self.jobs.pop(jid, None)
                if job_info is not None:
                    job_info.finished.set()


async def _start_job(job_tracker, request):
    pkdc('start_job: {}', request)
    await job_tracker.start_job(
        request['jid'], request['run_dir'], request['config']
    )
    return {}


async def _job_status(job_tracker, request):
    pkdc('job_status: {}', request)
    job_info = job_tracker.jobs.get(request['jid'])
    if job_info is None:
        return {'status': _JobStatus.NOT_STARTED.value}
    else:
        return {'status': job_info.status.value}


async def _cancel_job(job_tracker, request):
    job_info = job_tracker.jobs[request['jid']]
    if job_info.status is not _JobStatus.PENDING:
        return {'canceled': False}
    job_info.status = _JobStatus.CANCELED
    _write_status(_JobStatus.CANCELED, run_dir)
    job_info.process.terminate()
    with trio.move_on_after(_KILL_TIMEOUT_SECS):
        await job_info.finished.wait()
    job_info.process.kill()
    await job_info.finished.wait()
    return {'canceled': True}


_HANDLERS = {
    'start_job': _start_job,
    'job_status': _job_status,
    'cancel_job', _cancel_job,
}


async def _handle_conn(job_tracker, stream):
    with _catch_and_log_errors(Exception, 'error handling request'):
        try:
            request_bytes = bytearray()
            while True:
                chunk = await stream.receive_some(_CHUNK_SIZE)
                if not chunk:
                    break
                request_bytes += chunk
            request = pkjson.load_any(request_bytes)
            handler = _HANDLERS[request['action']]
            response = await handler(job_tracker, request)
            response_bytes = pkjson.dump_bytes(response)
        except Exception as exc:
            await stream.send_all(
                pkjson.dump_bytes({'error_string': repr(exc)})
            )
            # Let's also log the full error here
            raise
        else:
            await stream.send_all(response_bytes)


async def _main():
    with trio.socket.socket(family=trio.socket.AF_UNIX) as sock:
        # XX TODO: better strategy for handoff between runner instances
        # Clear out any stale socket file
        sock_path = srdb.runner_socket_path()
        pkio.unchecked_remove(sock_path)
        sock.bind(str(sock_path))
        sock.listen(_LISTEN_QUEUE)
        listener = trio.SocketListener(sock)

        async with trio.open_nursery() as nursery:
            job_tracker = _JobTracker(nursery)
            await trio.serve_listeners(
                functools.partial(_handle_conn, job_tracker), [listener]
            )


def start():
    """Starts the container runner."""
    trio.run(_main)


def start_dev():
    """Temporary hack for testing: starts the dev server + container runner."""
    import subprocess
