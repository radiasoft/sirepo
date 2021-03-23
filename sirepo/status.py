# -*- coding: utf-8 -*-
u"""Sirepo web server status for remote monitoring

:copyright: Copyright (c) 2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkcompat
from pykern import pkconfig
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp
from pykern.pkunit import pkre
from sirepo import api_perm
from sirepo import http_reply
from sirepo import server
from sirepo import simulation_db
from sirepo import uri_router
import datetime
import random
import re
import time


#: basic auth "app" initilized in `init_apis`
_basic_auth = None

_MAX_CALLS = 10

_SLEEP = 1

_SIM_TYPE = 'srw'

_SIM_NAME = 'Undulator Radiation'

_SIM_REPORT = 'initialIntensityReport'

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
    pkre(
        r'"isLoggedIn": true',
        pkcompat.from_bytes(uri_router.call_api('authState').data),
    )
    simulation_type = _SIM_TYPE
    res = uri_router.call_api(
        'findByNameWithAuth',
        dict(
            simulation_type=simulation_type,
            application_mode='default',
            simulation_name=_SIM_NAME,
        ),
    )
    m = re.search(r'\/source\/(\w+)"', pkcompat.from_bytes(res.data))
    if not m:
        raise RuntimeError('failed to find sid in resp={}'.format(res.data))
    i = m.group(1)
    d = simulation_db.read_simulation_json(simulation_type, sid=i)
    try:
        d.models.electronBeam.current = d.models.electronBeam.current + (random.random() / 10)
    except AttributeError:
        assert _SIM_TYPE == 'myapp', \
            f'{_SIM_TYPE} should be myapp or have models.electronBeam.current'
        pass
    d.simulationId = i
    d.report = _SIM_REPORT
    r = None
    try:
        resp = uri_router.call_api('runSimulation', data=d)
        for _ in range(_MAX_CALLS):
            r = simulation_db.json_load(resp.data)
            pkdlog('resp={}', r)
            if r.state == 'error':
                raise RuntimeError('simulation error: resp={}'.format(r))
            if r.state == 'completed':
                if 'initialIntensityReport' == d.report:
                    min_size = 50
                    if len(r.z_matrix) < min_size or len(r.z_matrix[0]) < min_size:
                        raise RuntimeError('received bad report output: resp={}', r)
                return
            d = r.nextRequest
            resp = uri_router.call_api('runStatus', data=d)
            time.sleep(_SLEEP)
        raise RuntimeError(
            'simulation timed out: seconds={} resp='.format(_MAX_CALLS * _SLEEP, r),
        )
    finally:
        try:
            uri_router.call_api('runCancel', data=d)
        except Exception:
            pass
