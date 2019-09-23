# -*- coding: utf-8 -*-
"""Common functionality that is shared between the server, supervisor, and driver.

Because this is going to be shared across the server, supervisor, and driver it
must be py2 compatible.

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkcollections, pkjson, pkconfig
from pykern.pkdebug import pkdp, pkdc, pkdlog, pkdexc
from sirepo import simulation_db, srdb
import aenum
import contextlib
import requests
import sirepo.mpi
import socket
import uuid


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
ACTION_CANCEL_JOB = 'cancel_job'

DEFAULT_IP = '127.0.0.1'
DEFAULT_PORT = 8001

class JobStatus(aenum.Enum):
    MISSING = 'missing'     # no data on disk, not currently running
    RUNNING = 'running'     # data on disk is incomplete but it's running
    ERROR = 'error'         # data on disk exists, but job failed somehow
    CANCELED = 'canceled'   # data on disk exists, but is incomplete
    COMPLETED = 'completed' # data on disk exists, and is fully usable



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


# TODO(e-carlin): These methods have the same structure. Abstract.
def compute_job_status(compute_model_name, run_dir, jhash):
    body = pkcollections.Dict(
        compute_model_name=compute_model_name,
        action=ACTION_COMPUTE_JOB_STATUS,
        run_dir=str(run_dir),
        jhash=jhash,
    )
    response = _request(body)
    return JobStatus(response.status)


def cancel_report_job(run_dir, jhash):
    body = pkcollections.Dict(
        action=ACTION_CANCEL_JOB,
        run_dir=str(run_dir),
        jhash=jhash,
    )
    return _request(body)


def run_extract_job(compute_model_name, run_dir, jhash, subcmd, *args):
    body = pkcollections.Dict(
        compute_model_name=compute_model_name,
        action=ACTION_RUN_EXTRACT_JOB,
        run_dir=str(run_dir),
        jhash=jhash,
        subcmd=subcmd,
        arg=pkjson.dump_pretty(args),
    )
    response = _request(body)
    return response.result

def start_compute_job(compute_model_name, sim_id, run_dir, jhash, cmd, tmp_dir, parallel):
    body = pkcollections.Dict(
        action=ACTION_START_COMPUTE_JOB,
        compute_model_name=compute_model_name,
        sim_id=sim_id,
        run_dir=str(run_dir),
        jhash=jhash,
        cmd=cmd,
        tmp_dir=str(tmp_dir),
        resource_class='parallel' if parallel else 'sequential',
    )
    _request(body)
    return {}

def _request(body):
    #TODO(e-carlin): uid is used to identify the proper broker for the reuqest
    # We likely need a better key and maybe we shouldn't expose this implementation
    # detail to the client.
    uid = simulation_db.uid_from_dir_name(body.run_dir)
    body.uid = uid
    body.req_id = str(uuid.uuid4())
    body.setdefault('resource_class', 'sequential')
    r = requests.post(cfg.supervisor_http_uri, json=body)
    return pkjson.load_any(r.content)



cfg = pkconfig.init(
    supervisor_http_uri=(
        'http://{}:{}/server'.format(DEFAULT_IP, DEFAULT_PORT),
        str,
        'uri to reach the supervisor for http connections',
    ),
    supervisor_ws_uri=(
        'ws://{}:{}/agent'.format(DEFAULT_IP, DEFAULT_PORT),
        str,
        'uri to reach the supervisor for websocket connections',
    ),
)