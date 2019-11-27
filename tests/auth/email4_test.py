# -*- coding: utf-8 -*-
u"""test token reuse

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest


def test_token_reuse(auth_fc):
    fc = auth_fc

    from pykern import pkconfig, pkunit, pkio
    from pykern.pkunit import pkok, pkre
    from pykern.pkdebug import pkdp

    r = fc.sr_post(
        'authEmailLogin',
        {'email': 'reuse@b.c', 'simulationType': fc.sr_sim_type},
    )
    fc.sr_email_confirm(fc, r)
    s = fc.sr_auth_state(userName='reuse@b.c')
    fc.sr_get('authLogout', {'simulation_type': fc.sr_sim_type})
    r = fc.sr_get(r.url, redirect=False)
    pkre('/login-fail/email', r.headers['Location'])
    fc.sr_auth_state(isLoggedIn=False)
