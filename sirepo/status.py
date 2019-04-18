# -*- coding: utf-8 -*-
u"""Sirepo web server status for remote monitoring

:copyright: Copyright (c) 2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function

from flask_basicauth import BasicAuth
from pykern import pkconfig
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp
from sirepo import api_perm
from sirepo import cookie
from sirepo import http_reply
from sirepo import server
from sirepo import simulation_db
from sirepo import uri_router
import datetime
import flask
import random
import re
import time


@api_perm.allow_cookieless_set_user
def api_serverStatus():
    """Allow for remote monitoring of the web server status. Authentication
    is done via Basic Auth. The username should be an existing sirepo uid.
    The status checks that a simple simulation can complete successfully
    within a short period of time.
    """
    if not _basic_auth.authenticate():
        return _basic_auth.challenge()
    uid = flask.request.authorization.username
    simulation_db.assert_id(uid)
    if not simulation_db.user_dir_name(uid).exists():
        raise RuntimeError('status user does not exist: {}'.format(uid))
    cookie.set_user(uid)
    _run_tests()
    return http_reply.gen_json_ok({
        'datetime': datetime.datetime.utcnow().isoformat(),
    })


def init_apis(app, *args, **kwargs):
    global cfg
    cfg = pkconfig.init(
        uid=pkconfig.Required(str, 'Sirepo status user id'),
        password=pkconfig.Required(str, 'Basic Auth password'),
    )
    app.config['BASIC_AUTH_USERNAME'] = cfg.uid
    app.config['BASIC_AUTH_PASSWORD'] = cfg.password
    global _basic_auth
    _basic_auth = BasicAuth(app)


def _run_tests():
    # Runs the SRW "Undulator Radiation" simulation's initialIntensityReport.
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
