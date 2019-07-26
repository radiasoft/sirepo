# -*- coding: utf-8 -*-
u"""Test sirepo.auth

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest
from pykern import pkcollections
from sirepo import srunit


@srunit.wrap_in_request(sim_types='myapp')
def test_login():
    from pykern import pkunit
    from pykern.pkdebug import pkdp
    from pykern.pkunit import pkeq, pkok, pkre
    from sirepo import auth
    import flask
    import sirepo.auth.guest
    import sirepo.cookie
    import sirepo.http_request

    r = auth.api_authState()
    pkre('LoggedIn": false.*Registration": false', r.data)
    delattr(flask.g, 'sirepo_cookie')
    auth.process_request()
    with pkunit.pkexcept('Unauthorized'):
        auth.logged_in_user()
    r = auth.require_user()
    pkeq(400, r.status_code, 'status should be BAD REQUEST')
    pkre('"routeName": "login"', r.data)
    sirepo.cookie.set_sentinel()
    # copying examples for new user takes time
    r = auth.login(sirepo.auth.guest)
    pkeq(None, r, 'user created')
    r = auth.api_authState()
    pkre('LoggedIn": true.*Registration": true', r.data)
    u = auth.logged_in_user()
    pkok(u, 'user should exist')
    r = auth.require_user()
    pkeq(400, r.status_code, 'status should be BAD REQUEST')
    pkre('"routeName": "completeRegistration"', r.data)
    flask.request = 'abcdef'
    def parse_json(*args, **kwargs):
        return pkcollections.Dict(simulationType='myapp', displayName='Joe Bob')
    setattr(sirepo.http_request, 'parse_json', parse_json)
    auth.api_authCompleteRegistration()
    r = auth.api_authState()
    pkre('Name": "Joe Bob".*In": true.*.*Registration": false', r.data)
