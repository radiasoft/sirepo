# -*- coding: utf-8 -*-
u"""Sirepo web server status for remote monitoring

:copyright: Copyright (c) 2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkconfig
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp
from sirepo import api_perm
from sirepo import http_reply
from sirepo import server
from sirepo import simulation_db
from sirepo import uri_router
import datetime
import re
import time


#: basic auth "app" initilized in `init_apis`
_basic_auth = None

_MAX_CALLS = 10

_SLEEP = 1

@api_perm.require_auth_basic
def api_serverStatus():
    """Allow for remote monitoring of the web server status.

    The user must be an existing sirepo uid.  The status checks
    that a simple simulation can complete successfully within a
    short period of time.
    """
    _run_tests()
    return http_reply.gen_json_ok({
        'datetime': datetime.datetime.utcnow().isoformat(),
    })


def init_apis(*args, **kwargs):
    pass


def _run_tests():
    """Runs the SRW "Undulator Radiation" simulation's initialIntensityReport"""
    simulation_type = 'srw'
    res = uri_router.call_api(
        server.api_findByName,
        dict(
            simulation_type=simulation_type,
            application_mode='default',
            simulation_name='Undulator Radiation',
        ),
    )
    m = re.search(r'\/source\/(\w+)"', res.data)
    if not m:
        raise RuntimeError('failed to find sid in resp={}'.format(res.data))
    i = m.group(1)
    d = simulation_db.read_simulation_json(simulation_type, sid=i)
    d.simulationId = i
    d.report = 'initialIntensityReport'
    r = None
    try:
        uri_router.call_api(server.api_runSimulation, data=d)
        for _ in range(_MAX_CALLS):
            time.sleep(_SLEEP)
            resp = uri_router.call_api(server.api_runStatus, data=d)
            r = simulation_db.json_load(resp.data)
            if r.state == 'error':
                raise RuntimeError('simulation error: resp={}'.format(r))
            if r.state == 'completed':
                min_size = 50
                if len(r.z_matrix) < min_size or len(r.z_matrix[0]) < min_size:
                    raise RuntimeError('received bad report output: resp={}', r)
                return
            d = r.nextRequest
        raise RuntimeError(
            'simulation timed out: seconds={} resp='.format(_MAX_CALLS * _SLEEP, r),
        )
    finally:
        try:
            uri_router.call_api(server.api_runCancel, data=d)
        except Exception:
            pass
