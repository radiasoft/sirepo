# -*- coding: utf-8 -*-
"""Common functionality that is shared between the server, supervisor, and driver.

Because this is going to be shared across the server, supervisor, and driver it
must be py2 compatible.

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function


from pykern import pkconfig
import aenum


# Actions that the sirepo server, supervisor, or driver may send.
# DRIVER_* : Action that originated from the driver
# SRSERVER_* : Action that originated from  the sirepo server
# SUPERVISOR_* : Action that originated from the supervisor
# TODO(e-carlin): Can we use an enum without manually serializing and deserializing?
# pkcollections.json doesn't support this: https://stackoverflow.com/questions/24481852/serialising-an-enum-member-to-json
ACTION_DRIVER_READY_FOR_WORK = 'driver_ready_for_work'
ACTION_DRIVER_REPORT_JOB_STARTED = 'driver_report_job_started'
ACTION_DRIVER_REPORT_JOB_STATUS = 'driver_report_job_status'
ACTION_DRIVER_EXTRACT_JOB_RESULTS = 'driver_extract_job_results'
ACTION_DRIVER_REPORT_JOB_STARTED = 'driver_report_job_started'

ACTION_SRSERVER_REPORT_JOB_STATUS = 'srserver_report_job_status'
ACTION_SRSERVER_RUN_EXTRACT_JOB = 'srserver_run_extract_job'
ACTION_SRSERVER_START_REPORT_JOB = 'srserver_start_report_job'

ACTION_SUPERVISOR_KEEP_ALIVE = 'supervisor_keep_alive'

DEFAULT_IP = '127.0.0.1'
DEFAULT_PORT = 8001
DEFAULT_WS_PATH = 'ws'

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
