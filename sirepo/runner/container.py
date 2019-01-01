# -*- coding: utf-8 -*-
u"""Run jobs in Docker.

:copyright: Copyright (c) 2018-2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from sirepo import runner, simulation_db
import base64
import contextlib
import docker
import functools
import json
import logging
from pykern.pkdebug import pkdp, pkdc, pkdlog, pkdexc
import redis
import requests
import shlex
import trio

# The redis key we use for the request list
_REQUEST_LIST_KEY = 'seq:job_queue'
# The redis key we use for the job status hash
_JOB_STATUS_HASH_KEY = 'hash:job_status'

# How often threaded blocking operations should wake up and check for Trio
# cancellation
_CANCEL_POLL_INTERVAL = 1

# Global connection pools (don't worry, they don't actually make any
# connections until we start using them)
_REDIS = redis.from_url('redis://localhost:6379/0')
_DOCKER = docker.from_env()


def _encode_request(request):
    return json.dumps(request).encode('utf-8')


def _decode_request(request):
    return json.loads(request.decode('utf-8'))


def _submit_request(request):
    pkdc('submitting request: {!r}', request)
    _REDIS.rpush(_REQUEST_LIST_KEY, _encode_request(request))


@contextlib.contextmanager
def _catch_and_log_errors(exc_type, msg, *args, **kwargs):
    try:
        yield
    except exc_type:
        pkdlog(msg, *args, **kwargs)
        pkdlog(pkdexc())


# Helper to call redis blpop in a async/cancellation-friendly way
async def _pop_encoded_request():
    while True:
        retval = await trio.run_sync_in_worker_thread(
            functools.partial(
                _REDIS.blpop, [_REQUEST_LIST_KEY], timeout=_CANCEL_POLL_INTERVAL
            )
        )
        if retval is not None:
            # it's a pair (key, popped value)
            return retval[1]


# Helper to call docker wait in a async/cancellation-friendly way
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


# The core request handler
async def _handle_request(encoded_request):
    with _catch_and_log_errors(Exception, 'error handling request {!r}', encoded_request):
        request = _decode_request(encoded_request)
        if request['type'] == 'start':
            # Technically a blocking call, but redis is fast and local so we
            # can get away with it
            _REDIS.hset(_JOB_STATUS_HASH_KEY, request['jid'], b'running')
            # Start the container
            container = await trio.run_sync_in_worker_thread(
                functools.partial(
                    _DOCKER.containers.run,
                    request['image'],
                    request['command'],
                    working_dir=request['working_dir'],
                    # {host path: {'bind': container path, 'mode': 'rw'}}
                    volumes=request['volumes'],
                    name=request['jid'],
                    auto_remove=True,
                    detach=True,
                    init=True,
                )
            )
            # Returns a dict like: {'Error': None, 'StatusCode': 0}
            # XX TODO but there may be a race condition where if the container
            # finishes before our call to wait() starts, then it just errors
            # out with docker.errors.NotFound
            pkdp(await _container_wait(container))
            # Technically a blocking call
            _REDIS.hset(_JOB_STATUS_HASH_KEY, request['jid'], b'finished')
        elif request['type'] == 'cancel':
            # This could fail, if the container doesn't exist or has already
            # stopped, but _catch_and_log_errors catch the issue. We might
            # want to catch and ignore expected errors like this, though,
            # rather than letting them escape to _catch_and_log_errors?
            container = _DOCKER.containers.get(request['jid'])
            container.stop()
            # Doesn't update status, because that will happen automatically
            # when it actually stops...
        else:
            raise RuntimeError(f'unknown request type: {request["type"]!r}')


async def _main():
    async with trio.open_nursery() as nursery:
        while True:
            encoded_request = await _pop_encoded_request()
            pkdc('handling request: {!r}', encoded_request)
            nursery.start_soon(_handle_request, encoded_request)


def serve():
    trio.run(_main)


################################################################
# Sirepo integration bits
################################################################

class ContainerJob(runner.JobBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._sent_start_request = False

    def _is_processing(self):
        return (self._sent_start_request
                and _REDIS.hget(_JOB_STATUS_HASH_KEY, self.jid) != b'finished')

    def _kill(self):
        _submit_request({'type': 'cancel', 'jid': self.jid})

    def _start(self):
        # XX TODO I suspect this is not the right place to do this but I don't
        # understand the status tracking flow yet.
        simulation_db.write_status('running', self.run_dir)
        # We can't just pass self.cmd directly to docker because we have to
        # detour through bash to set up our environment. But we do assume that
        # self.cmd is sufficiently well-behaved that shlex.quote will work.
        image = 'radiasoft/sirepo'
        docker_command = [
            '/bin/bash',
            '-c',
            '. ~/.bashrc && ' + ' '.join(shlex.quote(c) for c in self.cmd),
        ]
        _submit_request({
            'type': 'start',
            'jid': self.jid,
            'image': image,
            'command': docker_command,
            'working_dir': str(self.run_dir),
            'volumes': {str(self.run_dir):
                          {'bind': str(self.run_dir), 'mode': 'rw'}},
        })
        # XX TODO: This is a hack to avoid a race condition where
        # _is_processing would return False for a moment after we call this.
        # If we could wait for the scheduler daemon to acknowledge our request
        # before returning, this would be unnecessary.
        self._sent_start_request = True


def init_class(app, uwsgi):
    # XX TODO: what else should we do here? check if we can connect to redis
    # and the service is running?
    return ContainerJob
