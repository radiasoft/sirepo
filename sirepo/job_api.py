# -*- coding: utf-8 -*-
u"""Entry points for job execution

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkinspect, pkjson
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp, pkdpretty
from sirepo import api_perm
from sirepo import http_reply
from sirepo import http_request
from sirepo import job
from sirepo import simulation_db
from sirepo import srdb
from sirepo import srtime
from sirepo.template import template_common
import sirepo.auth
import calendar
import datetime
import requests
import sirepo.sim_data
import sirepo.template
import time


_YEAR = datetime.timedelta(365)


@api_perm.require_user
def api_runCancel():
    return _request()


@api_perm.require_user
def api_runSimulation():
    return _request(data=http_request.parse_data_input(validate=True))


@api_perm.require_user
def api_runStatus():
    data=http_request.parse_data_input()
    return _request(
        data=data,
        computeJobHash=data.computeJobHash,
    )


@api_perm.require_user
def api_simulationFrame(frame_id):
    def op(frame_args):
        return _request(
            data=frame_args,
            computeJobHash=frame_args.computeJobHash,
        )

    return template_common.get_simulation_frame(frame_id, op)


def init_apis(*args, **kwargs):
    pass


def _rfc1123(dt):
    return wsgiref.handlers.format_date_time(srtime.to_timestamp(dt))


def _request(**kwargs):
    b = _request_body(kwargs)
    import inspect
    b.setdefault(
        api=inspect.stack()[1][3],  # TODO(e-carlin): Use pkinspect.caller()
        reqId=job.unique_key(),
        uid=sirepo.auth.logged_in_user(),
    )
    r = requests.post(
        job.cfg.supervisor_uri,
        data=pkjson.dump_bytes(b),
        headers=PKDict({'Content-type': 'application/json'}),
    )
    r.raise_for_status()
    c = pkjson.load_any(r.content)
    # if 'error' in c or c.get('action') == 'error':
    #     pkdlog('reply={} request={}', c, b)
    #     # TODO(e-carlin): Something better
    #     raise RuntimeError('Error. Please try agin.')
    return c


def _request_body(kwargs):
    b = PKDict(kwargs)
    d = b.get('data') or http_request.parse_data_input()
    s = sirepo.sim_data.get_class(d)
    return b.pksetdefault(
        computeJobHash=lambda: s.compute_job_hash(d),
        computeModel=lambda: s.compute_model(d),
        isParallel=lambda: s.is_parallel(d),
    ).pksetdefault(
        computeJid=lambda: simulation_db.job_id(d),
    ).pksetdefault(
        # TODO(robnagler) remove this
        runDir=lambda: str(simulation_db.simulation_run_dir(d)),
    )
