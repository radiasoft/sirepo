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
import json
from pykern.pkdebug import pkdp, pkdc, pkdlog, pkdexc
import shlex
from sirepo import simulation_db
import trio

# XX TODO: fill in
# https://github.com/radiasoft/sirepo/issues/1499
_db_dir = XXX

# How often threaded blocking operations should wake up and check for Trio
# cancellation
_CANCEL_POLL_INTERVAL = 1

# Global connection pool (don't worry, it doesn't actually make any
# connections until we start using it)
_DOCKER = docker.from_env()

_CHUNK_SIZE = 4096
_LISTEN_QUEUE = 1000


@contextlib.contextmanager
def _catch_and_log_errors(exc_type, msg, *args, **kwargs):
    try:
        yield
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


class _JobStatus(aenum.Enum):
    NOT_STARTED = 'NOT_STARTED'
    RUNNING = 'RUNNING'
    FINISHED = 'FINISHED'


class _JobInfo:
    def __init__(self, jid, run_dir, status):
        self.jid = jid
        self.status = status
        self.run_dir = run_dir


class _JobTracker:
    def __init__(self, nursery):
        # XX TODO: eventually we'll need a way to stop this growing without
        # bound, perhaps by clarifying the split in responsibilities between
        # the on-disk simulation_db versus the in-memory status.
        self.jobs = {}
        self._nursery = nursery

    async def start_job(self, jid, config):
        await self._nursery.start(self._run_job, jid, config)

    async def _run_job(
            self, jid, run_dir, config, *, task_status=trio.TASK_STATUS_IGNORED
    ):
        # XX TODO: there are all kinds of race conditions here, e.g. if the
        # same jid gets started multiple times in parallel... we need to
        # revisit this once jids are globally unique, and possibly add
        # features like "if there is another job running with the same
        # user/sim/job but a different hash, then auto-cancel that other job"
        self.jobs[jid] = _JobInfo(jid, run_dir, _JobStatus.RUNNING)
        try:
            container = await trio.run_sync_in_worker_thread(
                functools.partial(
                    _DOCKER.containers.run,
                    config['image'],
                    config['command'],
                    working_dir=config['working_dir'],
                    # {host path: {'bind': container path, 'mode': 'rw'}}
                    volumes=config['volumes'],
                    name=jid,
                    auto_remove=True,
                    detach=True,
                    init=True,
                )
            )
            task_status.started()
            # Returns a dict like: {'Error': None, 'StatusCode': 0}
            # XX TODO but there may be a race condition where if the container
            # finishes before our call to wait() starts, then it just errors
            # out with docker.errors.NotFound
            with _catch_and_log_errors(
                    Exception, 'error waiting for container {}', jid
            ):
                pkdc(await _container_wait(container))
        finally:
            self.jobs[jid] = _JobStatus.FINISHED


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
        return {"status": _JobStatus.NOT_STARTED.value}
    else:
        return {"status": job_info.status.value}


async def _cancel_job(job_tracker, request):
    job_info = job_tracker.jobs[request['jid']]
    if job_info.status is not JobStatus.RUNNING:
        return {}
    simulation_db.write_result({'state': 'canceled'}, run_dir=job_info.run_dir)
    # XX TODO: this is what api_runCancel used to do, but we can't really do
    # it here. What should we do? (For a cancelled job, should we just delete
    # the run-dir entirely, once we have the full hash in the jid?)
    #
    # t = sirepo.template.import_module(data)
    # if hasattr(t, 'remove_last_frame'):
    #     t.remove_last_frame(run_dir)
    try:
        container = _DOCKER.containers.get(request['jid'])
        container.stop()
    except docker.errors.NotFound:
        # XX TODO: do we need to worry about a race condition where cancel
        # arrives just before start_job?
        # Probably a more reliable API for interactive jobs would be: the
        # frontend polls every X seconds to say that it wants to see the
        # results for {jid}, are they ready? And if it's not running, we start
        # it; if it's running, we do nothing; and if it's running but we
        # haven't seen a poll for the last X+Y seconds, then we automatically
        # cancel it. (This assumes improved jid's that include the hash.)
        # Of course batch jobs we only want to cancel when explicitly
        # requested, but in that case it involves a user clicking a button so
        # we don't really need to worry about race conditions.
        pass
    # Doesn't update status, because that will happen automatically
    # when it actually stops...
    return {}


_HANDLERS = {
    "start_job": _start_job,
    "job_status": _job_status,
    "cancel_job", _cancel_job,
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
            request = json.loads(request_bytes)
            handler = _HANDLERS[request["action"]]
            response = await handler(job_tracker, request)
            response_bytes = json.dumps(response).encode("ascii")
        except Exception as exc:
            await stream.send_all(
                json.dumps({'error_string': repr(exc)}).encode('ascii')
            )
            # Let's also log the full error here
            raise
        else:
            await stream.send_all(response_bytes)


async def _main():
    with trio.socket.socket(family=trio.socket.AF_UNIX) as sock:
        # XX TODO: better strategy for handoff between runner instances
        # Clear out any stale socket file
        try:
            os.unlink(_db_dir.join('runner.sock'))
        except OSError:
            pass
        sock.bind(_db_dir.join('runner.sock'))
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
