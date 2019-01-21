# -*- coding: utf-8 -*-
u"""Run jobs in Docker.

:copyright: Copyright (c) 2018-2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from sirepo import runner, simulation_db
import collections
import contextlib
import docker
import enum
import functools
import json
from pykern.pkdebug import pkdp, pkdc, pkdlog, pkdexc
import quart
import quart_trio
import requests
import shlex
import trio
import yarl

# XX TODO: should this be configurable somehow?
_HTTP_API_URL = yarl.URL('http://127.0.0.1:8001')

# How often threaded blocking operations should wake up and check for Trio
# cancellation
_CANCEL_POLL_INTERVAL = 1

# Global connection pools (don't worry, they don't actually make any
# connections until we start using them)
_DOCKER = docker.from_env()
_REQUESTS = requests.Session()

# The scheduler daemon's global state. _JOB_TRACKER is initialized lazily.
_JOB_TRACKER = None
_QUART_APP = quart_trio.QuartTrio(__name__)


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


class JobStatus(enum.Enum):
    NOT_STARTED = 'NOT_STARTED'
    RUNNING = 'RUNNING'
    FINISHED = 'FINISHED'


class JobTracker:
    def __init__(self, nursery):
        # XX TODO: eventually we'll need a way to stop this growing without
        # bound, perhaps by clarifying the split in responsibilities between
        # the on-disk simulation_db versus the in-memory status.
        self.jid_to_status = collections.defaultdict(
            lambda: JobStatus.NOT_STARTED
        )
        self._nursery = nursery

    async def start_job(self, jid, config):
        await self._nursery.start(self._run_job, jid, config)

    async def _run_job(
            self, jid, config, *, task_status=trio.TASK_STATUS_IGNORED
    ):
        # XX TODO: there are all kinds of race conditions here, e.g. if the
        # same jid gets started multiple times in parallel... we need to
        # revisit this once jids are globally unique, and possibly add
        # features like "if there is another job running with the same
        # user/sim/job but a different hash, then auto-cancel that other job"
        self.jid_to_status[jid] = JobStatus.RUNNING
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
            self.jid_to_status[jid] = JobStatus.FINISHED


@_QUART_APP.route('/jobs/<jid>', methods=['PUT'])
async def start_job(jid):
    pkdc('start_job', jid)
    config = await quart.request.get_json()
    await _JOB_TRACKER.start_job(jid, config)
    return ''


@_QUART_APP.route('/jobs/<jid>', methods=['GET'])
async def job_status(jid):
    pkdc('job_status: {}', jid)
    return _JOB_TRACKER.jid_to_status[jid].value
    return ''


@_QUART_APP.route('/jobs/<jid>/cancel', methods=['POST'])
async def cancel_job(jid):
    try:
        container = _DOCKER.containers.get(jid)
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
        # we don't really need to worried about race conditions.
        pass
    # Doesn't update status, because that will happen automatically
    # when it actually stops...
    return ''


# This is a temporary kluge until we get app.serve(...) or similar:
#   https://gitlab.com/pgjones/quart-trio/merge_requests/1
async def app_serve(app, host, port):
    import hypercorn
    import hypercorn.trio.run
    import quart.logging
    config = hypercorn.Config()
    config.host = host
    config.port = port
    config.access_log_format = '%(h)s %(r)s %(s)s %(b)s %(D)s'
    config.access_logger = quart.logging.create_serving_logger()
    config.error_logger = config.access_logger
    config.application_path = None
    hypercorn.trio.run.load_application = lambda *_: app
    await hypercorn.trio.run.run_single(config)


async def _main():
    async with trio.open_nursery() as nursery:
        global _JOB_TRACKER
        _JOB_TRACKER = JobTracker(nursery)
        await app_serve(_QUART_APP, _HTTP_API_URL.host, _HTTP_API_URL.port)


def serve():
    trio.run(_main)


################################################################
# Sirepo integration bits
################################################################

class ContainerJob(runner.JobBase):
    def _is_processing(self):
        r = _REQUESTS.get(_HTTP_API_URL / 'jobs' / self.jid)
        r.raise_for_status()
        return r.text == JobStatus.RUNNING.value

    def _kill(self):
        r = _REQUESTS.post(_HTTP_API_URL / 'jobs' / self.jid / 'cancel')
        r.raise_for_status()

    def _start(self):
        # This doesn't seem to be needed anymore? But I'm not 100% certain.
        #simulation_db.write_status('running', self.run_dir)
        # We can't just pass self.cmd directly to docker because we have to
        # detour through bash to set up our environment. But we do assume that
        # self.cmd is sufficiently well-behaved that shlex.quote will work.
        image = 'radiasoft/sirepo'
        docker_command = [
            '/bin/bash',
            '-c',
            '. ~/.bashrc && ' + ' '.join(shlex.quote(c) for c in self.cmd),
        ]
        config = {
            'image': image,
            'command': docker_command,
            'working_dir': str(self.run_dir),
            'volumes': {str(self.run_dir):
                          {'bind': str(self.run_dir), 'mode': 'rw'}},
        }
        r = _REQUESTS.put(_HTTP_API_URL / 'jobs' / self.jid, json=config)
        r.raise_for_status()


def init_class(app, uwsgi):
    # XX TODO: what else should we do here?
    return ContainerJob
