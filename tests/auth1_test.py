# -*- coding: utf-8 -*-
u"""Test sirepo.auth

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest
from pykern import pkcollections
from sirepo import srunit


@srunit.wrap_in_request(sim_types='myapp', want_user=False)
def test_login():
    from pykern import pkunit
    from pykern.pkdebug import pkdp
    from pykern.pkunit import pkeq, pkok, pkre, pkexcept
    from sirepo import auth
    import flask
    import sirepo.auth.guest
    import sirepo.cookie
    import sirepo.http_request

    r = auth.api_authState()
    pkre('LoggedIn": false.*Registration": false', r.data)
    delattr(flask.g, 'sirepo_cookie')
    auth.process_request()
    with pkunit.pkexcept('SRException.*routeName=login'):
        auth.logged_in_user()
    with pkexcept('SRException.*routeName=login'):
        auth.require_user()
    sirepo.cookie.set_sentinel()
    # copying examples for new user takes time
    with pkunit.pkexcept('SRException.*routeName=None'):
        r = auth.login(sirepo.auth.guest, sim_type='myapp')
    r = auth.api_authState()
    pkre('LoggedIn": true.*Registration": false', r.data)
    u = auth.logged_in_user()
    pkok(u, 'user should exist')
    # guests do not require completeRegistration
    auth.require_user()
