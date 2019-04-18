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
import datetime
import re
import time


#: basic auth "app" initilized in `init_apis`
_basic_auth = None


@api_perm.require_basic_auth
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
    res = server.api_findByName(simulation_type, 'default', 'Undulator Radiation')
    m = re.search(r'\/source\/(\w+)"', res)
    if not m:
        raise RuntimeError('status failed to find simulation_id: {}'.format(res))
    simulation_id = m.group(1)
    data = simulation_db.read_simulation_json(simulation_type, sid=simulation_id)
    data.simulationId = simulation_id
    data.report = 'initialIntensityReport'
    #TODO(pjm): don't call private server methods directly (_start_simulation() and _simulation_run_status())
    server._start_simulation(data)
    max_calls = 10
    for _ in range(max_calls):
        time.sleep(1)
        res = server._simulation_run_status(data)
        if res['state'] == 'error':
            raise RuntimeError('status received simulation error: {}'.format(res))
        if res['state'] == 'completed':
            min_size = 50
            if len(res['z_matrix']) < min_size or len(res['z_matrix'][0]) < min_size:
                raise RuntimeError('status received bad report output')
            return
    raise RuntimeError('status simulation failed to complete within {} seconds'.format(max_calls))
