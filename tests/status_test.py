# -*- coding: utf-8 -*-
u"""

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
import pytest


def test_basic(monkeypatch):
    from pykern import pkconfig
    from pykern.pkunit import pkeq
    from sirepo import srunit
    import base64
    p = 'pass'
    fc = srunit.flask_client(
        cfg=PKDict(
            SIREPO_AUTH_BASIC_PASSWORD=p,
            SIREPO_AUTH_BASIC_UID='dev-no-validate',
            SIREPO_AUTH_METHODS='basic:guest',
            SIREPO_FEATURE_CONFIG_API_MODULES='status',
        ),
        sim_types='myapp'
    )
    import sirepo.auth.basic

    u = fc.sr_login_as_guest()
    sirepo.auth.basic.cfg.uid = u
    import sirepo.status

    fc.cookie_jar.clear()
    # monkeypatch so status doesn't take so long
    sirepo.status._SIM_TYPE = 'myapp'
    sirepo.status._SIM_NAME = 'Scooby Doo'
    sirepo.status._SIM_REPORT = 'heightWeightReport'
    pkeq(401, fc.sr_get('serverStatus').status_code)
    r = fc.sr_get_json(
        'serverStatus',
        headers=PKDict(
            Authorization='Basic ' + base64.b64encode(u + ':' + p),
        ),
    )
    pkdp(r)
    pkeq('ok', r.state)
