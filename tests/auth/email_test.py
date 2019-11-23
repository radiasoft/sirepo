# -*- coding: utf-8 -*-
u"""Test auth.email

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest
import re


def test_different_email():
    fc, sim_type = _fc()

    from pykern import pkconfig, pkunit, pkio
    from pykern.pkunit import pkok, pkre
    from pykern.pkdebug import pkdp

    r = fc.sr_post(
        'authEmailLogin',
        {'email': 'diff@b.c', 'simulationType': sim_type},
    )
    s = fc.sr_auth_state(isLoggedIn=False)
    _confirm(fc, r)
    s = fc.sr_auth_state(isLoggedIn=True, needCompleteRegistration=True)
    fc.sr_post(
        'authCompleteRegistration',
        {
            'displayName': 'abc',
            'simulationType': sim_type,
        },
    )
    t = fc.sr_auth_state(userName='diff@b.c', displayName='abc')
    fc.sr_get('authLogout', {'simulation_type': sim_type})
    uid = fc.sr_auth_state(userName=None, isLoggedIn=False).uid
    r = fc.sr_post('authEmailLogin', {'email': 'x@y.z', 'simulationType': sim_type})
    _confirm(fc, r, 'xyz')
    uid2 = fc.sr_auth_state(displayName='xyz', isLoggedIn=True, userName='x@y.z').uid
    pkok(uid != uid2, 'did not get a new uid={}', uid)


def test_follow_email_auth_link_twice():
    fc, sim_type = _fc()

    from pykern import pkconfig, pkunit, pkio
    from pykern.pkunit import pkok, pkre
    from pykern.pkdebug import pkdp
    import json

    r = fc.sr_post(
        'authEmailLogin',
        {'email': 'follow@b.c', 'simulationType': sim_type},
    )
    # The link comes back in dev mode so we don't have to check email
    s = fc.sr_auth_state(isLoggedIn=False)
    fc.get(r.url)
    # get the url twice - should still be logged in
    d = fc.sr_get(r.url)
    assert not re.search(r'login-fail', d.data)
    _confirm(fc, r)
    fc.sr_get('authLogout', {'simulation_type': sim_type})
    # now logged out, should see login fail for bad link
    pkre('login-fail', fc.get(r.url).data)


def test_force_login():
    fc, sim_type = _fc()

    from pykern import pkcollections
    from pykern import pkconfig, pkunit, pkio
    from pykern.pkdebug import pkdp
    from pykern.pkunit import pkok, pkre, pkeq, pkexcept
    from sirepo import http_reply
    from sirepo import util

    # login as a new user, not in db
    r = fc.sr_post('authEmailLogin', {'email': 'force@b.c', 'simulationType': sim_type})
    fc.get(r.url)
    fc.sr_get('authLogout', {'simulation_type': sim_type})
    with pkexcept('SRException.*routeName.*login'):
        fc.sr_post('listSimulations', {'simulationType': sim_type})
    r = fc.sr_post('authEmailLogin', {'email': 'force@b.c', 'simulationType': sim_type})
    _confirm(fc, r)
    fc.sr_post(
        'authCompleteRegistration',
        {
            'displayName': 'xyz',
            'simulationType': sim_type,
        },
    )
    d = fc.sr_post('listSimulations', {'simulationType': sim_type})
    pkeq(1, len(d))


def test_guest_merge():
    fc, sim_type = _fc()

    from pykern.pkunit import pkeq
    from pykern.pkdebug import pkdp

    # Start as a guest user
    fc.sr_login_as_guest(sim_type)
    d = fc.sr_post(
        'listSimulations',
        {'simulationType': sim_type},
    )
    pkeq(1, len(d), 'expecting only one simulation: data={}', d)
    d = d[0].simulation
    # Copy a sim as a guest user
    d = fc.sr_post(
        'copySimulation',
        dict(
            simulationId=d.simulationId,
            simulationType=sim_type,
            name='guest-sim',
            folder='/',
        ),
    )
    guest_uid = fc.sr_auth_state().uid

    # Convert to email user
    r = fc.sr_post('authEmailLogin', {'email': 'guest.merge@b.com', 'simulationType': sim_type})
    s = fc.sr_auth_state(isLoggedIn=True, method='guest')
    _confirm(fc, r)
    fc.sr_post(
        'authCompleteRegistration',
        {
            'displayName': 'abc',
            'simulationType': sim_type,
        },
    )
    r = fc.sr_auth_state(method='email', uid=guest_uid)
    d = fc.sr_post(
        'listSimulations',
        {'simulationType': sim_type, 'search': {'simulationName': 'Scooby Doo'}},
    )
    d = d[0].simulation
    # Copy sim as an email user
    d = fc.sr_post(
        'copySimulation',
        dict(
            simulationId=d.simulationId,
            simulationType=sim_type,
            name='email-sim',
            folder='/',
        ),
    )
    fc.sr_get('authLogout', {'simulation_type': sim_type})

    # Login as email user
    r = fc.sr_post('authEmailLogin', {'email': 'guest.merge@b.com', 'simulationType': sim_type})
    _confirm(fc, r)
    d = fc.sr_post(
        'listSimulations',
        {'simulationType': sim_type},
    )
    # Sims from guest and email present
    pkeq([u'Scooby Doo', u'email-sim', u'guest-sim'], sorted([x.name for x in d]))


def test_happy_path():
    fc, sim_type = _fc()

    from pykern import pkconfig, pkunit, pkio
    from pykern.pkunit import pkok, pkre
    from pykern.pkdebug import pkdp

    # login as a new user, not in db
    r = fc.sr_post('authEmailLogin', {'email': 'happy@b.c', 'simulationType': sim_type})
    _confirm(fc, r)
    fc.sr_post(
        'authCompleteRegistration',
        {
            'displayName': 'abc',
            'simulationType': sim_type,
        },
    )
    fc.sr_post('listSimulations', {'simulationType': sim_type})
    uid = fc.sr_auth_state(
        avatarUrl='https://www.gravatar.com/avatar/6932801af90f249078f2a3677178ca51?d=mp&s=40',
        displayName='abc',
        isLoggedIn=True,
        userName='happy@b.c',
    ).uid
    r = fc.sr_get('authLogout', {'simulation_type': sim_type})
    fc.sr_auth_state(
        displayName=None,
        isLoggedIn=False,
        needCompleteRegistration=False,
        uid=uid,
        userName=None,
    )


def test_invalid_method():
    fc, sim_type = _fc()

    from pykern import pkconfig, pkunit, pkio
    from pykern.pkunit import pkok, pkre
    from pykern.pkdebug import pkdp

    # login as a new user, not in db
    r = fc.sr_post('authEmailLogin', {'email': 'will-be-invalid@b.c', 'simulationType': sim_type})
    _confirm(fc, r)
    fc.sr_post(
        'authCompleteRegistration',
        {
            'displayName': 'abc',
            'simulationType': sim_type,
        },
    )
    fc.sr_post('listSimulations', {'simulationType': sim_type})
    import sirepo.auth
    sirepo.auth.cfg.methods = set(['guest'])
    sirepo.auth.cfg.deprecated_methods = set()
    sirepo.auth.visible_methods = sirepo.auth.valid_methods = tuple(sirepo.auth.cfg.methods)
    sirepo.auth.non_guest_methods = tuple()
    fc.sr_auth_state(
        displayName=None,
        isLoggedIn=False,
        needCompleteRegistration=False,
        uid=None,
        userName=None,
    )


def test_oauth_conversion(monkeypatch):
    """See `x_test_oauth_conversion_setup`"""
    fc, sim_type = _fc()

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
        fc.sr_post('listSimulations', {'simulationType': sim_type})
    r = fc.sr_get('authGithubLogin', {'simulation_type': sim_type}, redirect=False)
    pkre(oc.values.state, r.headers['Location'])
    state = oc.values.state
    fc.sr_get('authGithubAuthorized', query={'state': state})
    r = fc.sr_post(
        'authEmailLogin',
        {'email': 'emailer@test.com', 'simulationType': sim_type},
    )
    fc.sr_auth_state(isLoggedIn=True, method='github', uid=uid)
    _confirm(fc, r)
    fc.sr_auth_state(
        isLoggedIn=True,
        method='email',
        uid=uid,
        userName='emailer@test.com',
    )

def test_token_expired(monkeypatch):
    fc, sim_type = _fc()

    from sirepo import srtime

    r = fc.sr_post(
        'authEmailLogin',
        {'email': 'expired@b.c', 'simulationType': sim_type},
    )
    login_url = r.url
    srtime.adjust_time(1)
    r = fc.get(login_url)
    s = fc.sr_auth_state(isLoggedIn=False)


def test_token_reuse():
    fc, sim_type = _fc()

    from pykern import pkconfig, pkunit, pkio
    from pykern.pkunit import pkok, pkre
    from pykern.pkdebug import pkdp

    r = fc.sr_post(
        'authEmailLogin',
        {'email': 'reuse@b.c', 'simulationType': sim_type},
    )
    _confirm(fc, r)
    s = fc.sr_auth_state(userName='reuse@b.c')
    fc.sr_get('authLogout', {'simulation_type': sim_type})
    r = fc.sr_get(r.url, redirect=False)
    pkre('/login-fail/email', r.headers['Location'])
    fc.sr_auth_state(isLoggedIn=False)


def test_oauth_conversion_setup(monkeypatch):
    """Prepares data for auth conversion

    You need to run this as a test (no other cases), and then:
        rm -rf email_data
        mv email_work email_data

    Also grab the cookie output, and add it to test_oauth_conversion
    """
    fc, sim_type = _fc(github_deprecated=False)

    from pykern import pkcollections
    from pykern.pkdebug import pkdlog
    from pykern.pkunit import pkok, pkre, pkeq
    from sirepo.auth import github
    from sirepo import github_srunit

    oc = github_srunit.MockOAuthClient(monkeypatch, 'emailer')
    fc.sr_get('authGithubLogin', {'simulation_type': sim_type}, redirect=False)
    t = fc.sr_auth_state(userName=None, isLoggedIn=False, method=None)
    state = oc.values.state
    r = fc.sr_get('authGithubAuthorized', query={'state': state})
    uid = fc.sr_auth_state(
        displayName=None,
        method='github',
        needCompleteRegistration=True,
        userName='emailer',
    ).uid
    fc.sr_get('authLogout', {'simulation_type': sim_type})


def _confirm(fc, resp, display_name=None):
    from pykern.pkcollections import PKDict

    fc.sr_get(resp.url)
    m = re.search(r'/(\w+)$', resp.url)
    assert m
    r = PKDict(token=m.group(1))
    if display_name:
        r.displayName = display_name
    fc.sr_post(
        resp.url,
        r,
        raw_response=True,
    )


def _fc(github_deprecated=True):

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
    if github_deprecated:
        cfg['SIREPO_AUTH_DEPRECATED_METHODS'] = 'github'
    else:
        cfg['SIREPO_AUTH_METHODS'] += ':github'
    fc = srunit.flask_client(cfg=cfg)
    # set the sentinel
    fc.cookie_jar.clear()
    fc.sr_get_root(sim_type)
    return fc, sim_type
