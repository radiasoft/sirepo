# -*- coding: utf-8 -*-
u"""Test auth.email

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest


def test_different_email():
    fc, sim_type = _fc()

    from pykern import pkconfig, pkunit, pkio
    from pykern.pkunit import pkok, pkre
    from pykern.pkdebug import pkdp
    import re

    r = fc.sr_post(
        'authEmailLogin',
        {'email': 'a@b.c', 'simulationType': sim_type},
    )
    s = fc.sr_auth_state(isLoggedIn=False)
    fc.get(r.url)
    s = fc.sr_auth_state(isLoggedIn=True, needCompleteRegistration=True)
    fc.sr_post(
        'authCompleteRegistration',
        {
            'displayName': 'abc',
            'simulationType': sim_type,
        },
    )
    t = fc.sr_auth_state(userName='a@b.c', displayName='abc')
    r = fc.sr_get('authLogout', {'simulation_type': sim_type})
    pkre('/{}$'.format(sim_type), r.headers['Location'])
    uid = fc.sr_auth_state(userName=None, isLoggedIn=False).uid
    r = fc.sr_post('authEmailLogin', {'email': 'x@y.z', 'simulationType': sim_type})
    fc.get(r.url)
    fc.sr_post(
        'authCompleteRegistration',
        {
            'displayName': 'xyz',
            'simulationType': sim_type,
        },
    )
    uid2 = fc.sr_auth_state(displayName='xyz', isLoggedIn=True, userName='x@y.z').uid
    pkok(uid != uid2, 'did not get a new uid={}', uid)


def test_force_login():
    fc, sim_type = _fc()

    from pykern import pkcollections
    from pykern import pkconfig, pkunit, pkio
    from pykern.pkdebug import pkdp
    from pykern.pkunit import pkok, pkre, pkeq
    from sirepo import http_reply
    import re

    # login as a new user, not in db
    r = fc.sr_post('authEmailLogin', {'email': 'a@b.c', 'simulationType': sim_type})
    fc.get(r.url)
    fc.sr_get('authLogout', {'simulation_type': sim_type})
    r = fc.sr_post('listSimulations', {'simulationType': sim_type}, raw_response=True)
    pkeq(http_reply.SR_EXCEPTION_STATUS, r.status_code)
    d = pkcollections.json_load_any(r.data)
    pkeq(http_reply.SR_EXCEPTION_STATE, d.state)
    pkeq('login', d.srException.routeName)
    r = fc.sr_post('authEmailLogin', {'email': 'a@b.c', 'simulationType': sim_type})
    fc.get(r.url)
    d = fc.sr_post('listSimulations', {'simulationType': sim_type})
    pkeq(1, len(d))


def test_happy_path():
    fc, sim_type = _fc()

    from pykern import pkconfig, pkunit, pkio
    from pykern.pkunit import pkok, pkre
    from pykern.pkdebug import pkdp
    import re

    # login as a new user, not in db
    r = fc.sr_post('authEmailLogin', {'email': 'a@b.c', 'simulationType': sim_type})
    fc.get(r.url)
    fc.sr_post(
        'authCompleteRegistration',
        {
            'displayName': 'abc',
            'simulationType': sim_type,
        },
    )
    fc.sr_post('listSimulations', {'simulationType': sim_type})
    uid = fc.sr_auth_state(
        avatarUrl='https://www.gravatar.com/avatar/5d60d4e28066df254d5452f92c910092?d=mp&s=40',
        displayName='abc',
        isLoggedIn=True,
        userName='a@b.c',
    ).uid
    r = fc.sr_get('authLogout', {'simulation_type': sim_type})
    pkre('/{}$'.format(sim_type), r.headers['Location'])
    fc.sr_auth_state(
        displayName=None,
        isLoggedIn=False,
        needCompleteRegistration=False,
        uid=uid,
        userName=None,
    )


def test_oauth_conversion(monkeypatch):
    """See `x_test_oauth_conversion_setup`"""
    fc, sim_type = _fc()

    from pykern import pkcollections
    from pykern.pkdebug import pkdp
    from pykern.pkunit import pkok, pkre, pkeq
    from pykern import pkunit
    from pykern import pkio
    from sirepo.auth import github
    from sirepo import github_srunit
    from sirepo import server
    import re
    import shutil

    pkio.unchecked_remove(server._app.sirepo_db_dir)
    pkunit.data_dir().join('db').copy(server._app.sirepo_db_dir)
    fc.cookie_jar.clear()
    fc.set_cookie('localhost', 'sirepo_dev', 'Z0FBQUFBQmN2bGQzaGc1MmpCRkxIOWNpWi1yd1JReXUxZG5FV2VqMjFwU2w2cmdOSXhlaWVkOC1VUzVkLVR5NzdiS080R3p1aGUwUEFfdmpmdDcxTmJlOUR2eXpJY2l1YUVWaUVVa3dCYXpnZGIwTV9fei1iTWNCdkp0eXJVY0Ffenc2SVoxSUlLYVM=')
    oc = github_srunit.MockOAuthClient(monkeypatch, 'emailer')
    uid = fc.sr_auth_state(isLoggedIn=False, method='github').uid
    r = fc.sr_post('listSimulations', {'simulationType': sim_type})
    pkeq('loginWith', r.srException.routeName)
    pkeq('github', r.srException.params.method)
    r = fc.sr_get('authGithubLogin', {'simulation_type': sim_type})
    state = oc.values.state
    pkeq(302, r.status_code)
    pkre(state, r.headers['location'])
    fc.sr_get('authGithubAuthorized', query={'state': state})
    r = fc.sr_post(
        'authEmailLogin',
        {'email': 'emailer@test.com', 'simulationType': sim_type},
    )
    fc.sr_auth_state(isLoggedIn=True, method='github', uid=uid)
    fc.get(r.url)
    fc.sr_auth_state(
        isLoggedIn=True,
        method='email',
        uid=uid,
        userName='emailer@test.com',
    )


def test_token_reuse():
    fc, sim_type = _fc()

    from pykern import pkconfig, pkunit, pkio
    from pykern.pkunit import pkok, pkre
    from pykern.pkdebug import pkdp
    import re

    r = fc.sr_post(
        'authEmailLogin',
        {'email': 'a@b.c', 'simulationType': sim_type},
    )
    login_url = r.url
    r = fc.get(r.url)
    s = fc.sr_auth_state(userName='a@b.c')
    r = fc.sr_get('authLogout', {'simulation_type': sim_type})
    r = fc.get(login_url)
    s = fc.sr_auth_state(isLoggedIn=False)


def x_test_oauth_conversion_setup(monkeypatch):
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
    import re

    oc = github_srunit.MockOAuthClient(monkeypatch, 'emailer')
    fc.sr_get(
        'oauthLogin',
        {
            'simulation_type': sim_type,
            'oauth_type': github.DEFAULT_OAUTH_TYPE,
        },
    )
    t = fc.sr_auth_state(userName=None, isLoggedIn=False, method=None)
    state = oc.values.state
    r = fc.sr_get(
        'oauthAuthorized',
        {
            'oauth_type': github.DEFAULT_OAUTH_TYPE,
        },
        query={'state': state},
    )
    uid = fc.sr_auth_state(
        displayName=None,
        method='github',
        needCompleteRegistration=True,
        userName='emailer',
    ).uid
    fc.sr_get('authLogout', {'simulation_type': sim_type})
    pkdlog(fc.cookie_jar)
    return


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
