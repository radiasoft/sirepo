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
from sirepo import simulation_db
import aenum
import requests
import uuid


# Actions that the sirepo server, supervisor, or driver may send.
# TODO(e-carlin): Can we use an enum without manually serializing
# and deserializing?
ACTION_CANCEL_JOB = 'cancel_job'
ACTION_COMPUTE_JOB_STATUS = 'compute_job_status'
ACTION_ERROR = 'error'
ACTION_KEEP_ALIVE = 'keep_alive'
ACTION_KILL = 'kill'
ACTION_READY_FOR_WORK = 'ready_for_work'
ACTION_RUN_EXTRACT_JOB = 'run_extract_job'
ACTION_START_COMPUTE_JOB = 'start_compute_job'

DEFAULT_IP = '127.0.0.1'
DEFAULT_PORT = 8001


# TODO(e-carlin): Use enums or string constants (like ACTIONS) not both.
class JobStatus(aenum.Enum):
    MISSING = 'missing'     # no data on disk, not currently running
    RUNNING = 'running'     # data on disk is incomplete but it's running
    ERROR = 'error'         # data on disk exists, but job failed somehow
    CANCELED = 'canceled'   # data on disk exists, but is incomplete
    COMPLETED = 'completed' # data on disk exists, and is fully usable
    PENDING = 'pending' # job has been sent to supervisor but hasn't started running


def init_by_server(app):
    """Initialize module"""
    from sirepo import job_api
    from sirepo import uri_router

    uri_router.register_api_module(job_api)


# TODO(e-carlin): These methods have the same structure. Abstract.
def compute_job_status(jid, run_dir, jhash, parallel):
    body = pkcollections.Dict(
        jid=jid,
        action=ACTION_COMPUTE_JOB_STATUS,
        run_dir=str(run_dir),
        jhash=jhash,
        parallel=parallel,

    )
    response = _request(body)
    return JobStatus(response.status)


def cancel_report_job(jid, run_dir, jhash):
    body = pkcollections.Dict(
        jid=jid,
        action=ACTION_CANCEL_JOB,
        run_dir=str(run_dir),
        jhash=jhash,
    )
    return _request(body)


def run_extract_job(jid, run_dir, jhash, subcmd, *args):
    body = pkcollections.Dict(
        jid=jid,
        action=ACTION_RUN_EXTRACT_JOB,
        run_dir=str(run_dir),
        jhash=jhash,
        subcmd=subcmd,
        arg=pkjson.dump_pretty(args),
    )
    response = _request(body)
    # TODO(e-carlin): Caller expecting (res, err). This doesn't return that
    return response.result


def start_compute_job(jid, sim_id, run_dir, jhash, cmd, tmp_dir, parallel):
    body = pkcollections.Dict(
        action=ACTION_START_COMPUTE_JOB,
        jid=jid,
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
    # TODO(e-carlin): uid is used to identify the proper broker for the reuqest
    # We likely need a better key and maybe we shouldn't expose this
    # implementation detail to the client.
    uid = simulation_db.uid_from_dir_name(body.run_dir)
    body.uid = uid
    body.req_id = str(uuid.uuid4())
    body.setdefault('resource_class', 'sequential')
    r = requests.post(cfg.job_server_http_uri, json=body)
    r.raise_for_status()
    c = pkjson.load_any(r.content)
    if 'error' in c or c.get('action') == 'error':
        pkdlog('Error: {}', c)
        raise Exception('Error. Please try agin.') # TODO(e-carlin): Something better
    return c


cfg = pkconfig.init(
    job_server_http_uri=(
        'http://{}:{}/server'.format(DEFAULT_IP, DEFAULT_PORT),
        str,
        'uri to reach the job server for http connections',
    ),
    job_server_ws_uri=(
        'ws://{}:{}/agent'.format(DEFAULT_IP, DEFAULT_PORT),
        str,
        'uri to reach the job server for websocket connections',
    ),
)
