# -*- coding: utf-8 -*-
u"""Test auth.email

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest
import re


def test_oauth_conversion(auth_fc, monkeypatch):
    """See `x_test_oauth_conversion_setup`"""
    fc = auth_fc

    from pykern import pkcollections
    from pykern.pkdebug import pkdp
    from pykern.pkunit import pkok, pkre, pkeq, pkexcept, pkfail
    from pykern import pkunit
    from pykern import pkio
    from sirepo.auth import github
    from sirepo import github_srunit
    from sirepo import server
    import sirepo.util
    import shutil

    pkio.unchecked_remove(server._app.sirepo_db_dir)
    pkunit.data_dir().join('db').copy(server._app.sirepo_db_dir)
    fc.cookie_jar.clear()
    fc.set_cookie('localhost', 'sirepo_dev', 'Z0FBQUFBQmN2bGQzaGc1MmpCRkxIOWNpWi1yd1JReXUxZG5FV2VqMjFwU2w2cmdOSXhlaWVkOC1VUzVkLVR5NzdiS080R3p1aGUwUEFfdmpmdDcxTmJlOUR2eXpJY2l1YUVWaUVVa3dCYXpnZGIwTV9fei1iTWNCdkp0eXJVY0Ffenc2SVoxSUlLYVM=')
    oc = github_srunit.MockOAuthClient(monkeypatch, 'emailer')
    uid = fc.sr_auth_state(isLoggedIn=False, method='github').uid
    with pkexcept('SRException.*method.*github.*routeName=loginWith'):
        fc.sr_post('listSimulations', {'simulationType': fc.sr_sim_type})
    r = fc.sr_get('authGithubLogin', {'simulation_type': fc.sr_sim_type}, redirect=False)
    pkre(oc.values.state, r.headers['Location'])
    state = oc.values.state
    fc.sr_get('authGithubAuthorized', query={'state': state})
    r = fc.sr_post(
        'authEmailLogin',
        {'email': 'emailer@test.com', 'simulationType': fc.sr_sim_type},
    )
    fc.sr_auth_state(isLoggedIn=True, method='github', uid=uid)
    fc.sr_email_confirm(fc, r)
    fc.sr_auth_state(
        isLoggedIn=True,
        method='email',
        uid=uid,
        userName='emailer@test.com',
    )
