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
    from pykern import pkunit, pkcompat
    from pykern.pkunit import pkeq, pkok, pkre, pkfail, pkexcept
    from sirepo import auth
    import flask
    import sirepo.api
    import sirepo.auth.guest
    import sirepo.cookie
    import sirepo.http_request
    import sirepo.uri_router
    import sirepo.util

    r = sirepo.uri_router.call_api('authState')
    pkre('LoggedIn": false.*Registration": false', pkcompat.from_bytes(r.data))
    with pkunit.pkexcept('SRException.*routeName=login'):
        auth.logged_in_user()
    with pkexcept('SRException.*routeName=login'):
        auth.require_user()
    sirepo.cookie.set_sentinel()
    # copying examples for new user takes time
    try:
        # TODO(rorour): get sapi from current request
        r = auth.login(sirepo.auth.guest, sim_type='myapp', sapi=sirepo.api.Base())
        pkfail('expecting sirepo.util.Response')
    except sirepo.util.Response as e:
        r = e.sr_args.response
    pkre(r'LoggedIn":\s*true.*Registration":\s*false', pkcompat.from_bytes(r.data))
    u = auth.logged_in_user()
    pkok(u, 'user should exist')
    # guests do not require completeRegistration
    auth.require_user()
