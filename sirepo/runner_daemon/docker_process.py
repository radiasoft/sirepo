# -*- coding: utf-8 -*-
u"""sirepo package

:copyright: Copyright (c) 2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function

import contextlib
import docker
import functools
import re
import requests
import shlex
from sirepo.template import template_common
import trio

# How often threaded blocking operations should wake up and check for Trio
# cancellation
_CANCEL_POLL_INTERVAL = 1

# Global connection pools (don't worry, it won't actually make any connections
# until we start using it)
_DOCKER = docker.from_env()

def _container_name(run_dir):
    # Docker container names have to start with [a-zA-Z0-9], and after that
    # can also contain [_.-].
    return 'sirepo-report-' + str(run_dir).replace('/', '-')


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


async def _clear_container(name):
    try:
        old_container = await trio.run_sync_in_worker_thread(
            _DOCKER.containers.get, name
        )
    except docker.errors.NotFound:
        pass
    else:
        await trio.run_sync_in_worker_thread(old_container.remove)


async def start(run_dir, cmd):
    run_log_path = run_dir.join(template_common.RUN_LOG)

    # We can't just pass the cmd directly to docker because we have to detour
    # through bash to set up our environment. But we do assume that it's
    # sufficiently well-behaved that shlex.quote will work.
    docker_cmd = [
        '/bin/bash',
        '-c',
        '. ~/.bashrc && ' + ' '.join(shlex.quote(c) for c in cmd),
    ]

    name = _container_name(run_dir)

    await _clear_container(name)

    container = await trio.run_sync_in_worker_thread(
        functools.partial(
            _DOCKER.containers.run,
            'radiasoft/sirepo',
            docker_cmd,
            working_dir=str(run_dir),
            # {host path: {'bind': container path, 'mode': 'rw'}}
            volumes={str(run_dir): {'bind': str(run_dir), 'mode': 'rw'}},
            name=name,
            detach=True,
            init=True,
        )
    )

    return _DockerProcess(container)


class _DockerProcess:
    def __init__(self, container):
        self._container = container

    async def kill(self, grace_period):
        with contextlib.suppress(docker.errors.NotFound):
            await trio.run_sync_in_worker_thread(
                functools.partial(self._container.stop, timeout=grace_period)
            )

    async def wait(self):
        result = await _container_wait(self._container)
        await trio.run_sync_in_worker_thread(self._container.remove)
        return result['StatusCode']
