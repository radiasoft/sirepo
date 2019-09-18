# -*- coding: utf-8 -*-
"""Client for communicating with job_supervisor

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function


from pykern import pkcollections, pkjson, pkconfig
from pykern.pkdebug import pkdp, pkdc, pkdlog, pkdexc
from sirepo import job
from sirepo import simulation_db
from sirepo import srdb
import aenum
import contextlib
import requests
import socket
import uuid
import sirepo.mpi


class JobStatus(aenum.Enum):
    MISSING = 'missing'     # no data on disk, not currently running
    RUNNING = 'running'     # data on disk is incomplete but it's running
    ERROR = 'error'         # data on disk exists, but job failed somehow
    CANCELED = 'canceled'   # data on disk exists, but is incomplete
    COMPLETED = 'completed' # data on disk exists, and is fully usable


def _request(body):
    #TODO(e-carlin): uid is used to identify the proper broker for the reuqest
    # We likely need a better key and maybe we shouldn't expose this implementation
    # detail to the client.
    uid = simulation_db.uid_from_dir_name(body['run_dir'])
    body['uid'] = uid
    body['source'] = 'server'
    body['rid'] = str(uuid.uuid4())
    body.setdefault('resource_class', 'sequential')
    r = requests.post(cfg.supervisor_http_uri, json=body)
    return pkjson.load_any(r.content)

def start_compute_job(run_dir, jhash, backend, cmd, tmp_dir, parallel):
    body = {
        'action': job.ACTION_START_COMPUTE_JOB,
        'run_dir': str(run_dir),
        'jhash': jhash,
        'backend': backend,
        'cmd': cmd,
        'tmp_dir': str(tmp_dir),
        'resource_class': 'parallel' if parallel else 'sequential',
    }
    _request(body)
    return {}


def compute_job_status(run_dir, jhash):
    body = {
        'action': job.ACTION_COMPUTE_JOB_STATUS,
        'run_dir': str(run_dir),
        'jhash': jhash,
    }
    response = _request(body)
    return JobStatus(response.status)


def cancel_report_job(run_dir, jhash):
    body = pkcollections.Dict(
        action='cancel_compute_job',
        run_dir=str(run_dir),
        jhash=jhash,
    )
    res = _request(body) 
    return res
    # return _rpc({
    #     'action': 'cancel_report_job', 'run_dir': str(run_dir), 'jhash': jhash,
    # })


def run_extract_job(run_dir, jhash, subcmd, *args):
    body = ({
        'action': job.ACTION_RUN_EXTRACT_JOB,
        'run_dir': str(run_dir),
        'jhash': jhash,
        'subcmd': subcmd,
        'arg': pkjson.dump_pretty(args),
    })
    response = _request(body)
    return response.result

cfg = pkconfig.init(
    supervisor_http_uri=(job.cfg.supervisor_http_uri, str, 'the uri to reach the supervisor on')
)