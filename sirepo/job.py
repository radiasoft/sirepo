# -*- coding: utf-8 -*-
"""Common functionality that is shared between the server, supervisor, and driver.

Because this is going to be shared across the server, supervisor, and driver it
must be py2 compatible.

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkconfig


# Actions that the sirepo server, supervisor, or driver may send.
# TODO(e-carlin): Can we use an enum without manually serializing and deserializing?
# pkcollections.json doesn't support this: https://stackoverflow.com/questions/24481852/serialising-an-enum-member-to-json
ACTION_EXTRACT_JOB_RESULTS = 'extract_job_results'
ACTION_KEEP_ALIVE = 'keep_alive'
ACTION_READY_FOR_WORK = 'ready_for_work'
ACTION_COMPUTE_JOB_STARTED = 'compute_job_started'
ACTION_COMPUTE_JOB_STATUS = 'compute_job_status'
ACTION_RUN_EXTRACT_JOB = 'run_extract_job'
ACTION_START_COMPUTE_JOB = 'start_compute_job'

DEFAULT_IP = '127.0.0.1'
DEFAULT_PORT = 8001

cfg = None


def init_by_server(app):
    """Initialize module"""
    global cfg
    cfg = pkconfig.init(
        supervisor_http_uri=(
            'http://{}:{}'.format(DEFAULT_IP, DEFAULT_PORT),
            str,
            'uri to reach the supervisor for http connections',
        ),
        supervisor_ws_uri=(
            'ws://{}:{}/{}'.format(DEFAULT_IP, DEFAULT_PORT, DEFAULT_WS_PATH),
            str,
            'uri to reach the supervisor for websocket connections',
        ),
    )
    from sirepo import job_api
    from sirepo import uri_router

    uri_router.register_api_module(job_api)
