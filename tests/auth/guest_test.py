# -*- coding: utf-8 -*-
u"""Test auth.guest

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from __future__ import absolute_import, division, print_function
import pytest


def test_happy_path():
    fc, sim_type = _fc()

    from pykern import pkconfig, pkunit, pkio
    from pykern.pkunit import pkok, pkre, pkeq
    from pykern.pkdebug import pkdp
    import re

    r = fc.sr_get('authGuestLogin', {'simulation_type': sim_type})
    pkeq(302, r.status_code)
    pkre(sim_type, r.headers['location'])
    fc.sr_post('listSimulations', {'simulationType': sim_type})
    uid = fc.sr_auth_state(
        displayName='Guest User',
        isLoggedIn=True,
        userName=None,
    ).uid


def _fc():
    from pykern.pkdebug import pkdp
    from sirepo import srunit

    sim_type = 'myapp'
    cfg = {
        'SIREPO_AUTH_METHODS': 'email:guest',
        'SIREPO_AUTH_EMAIL_FROM_EMAIL': 'x',
        'SIREPO_AUTH_EMAIL_FROM_NAME': 'x',
        'SIREPO_AUTH_EMAIL_SMTP_PASSWORD': 'x',
        'SIREPO_AUTH_EMAIL_SMTP_SERVER': 'dev',
        'SIREPO_AUTH_EMAIL_SMTP_USER': 'x',
        'SIREPO_AUTH_GITHUB_CALLBACK_URI': '/uri',
        'SIREPO_AUTH_GITHUB_KEY': 'key',
        'SIREPO_AUTH_GITHUB_SECRET': 'secret',
        'SIREPO_FEATURE_CONFIG_SIM_TYPES': sim_type,
    }
    fc = srunit.flask_client(cfg=cfg)
    # set the sentinel
    fc.cookie_jar.clear()
    fc.sr_get_root(sim_type)
    return fc, sim_type
