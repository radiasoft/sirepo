# -*- coding: utf-8 -*-
u"""Test github oauth

:copyright: Copyright (c) 2016-2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest


def test_guest_merge(monkeypatch):
    from pykern.pkdebug import pkdp
    from pykern.pkunit import pkfail, pkok, pkeq, pkre

    fc, sim_type, oc = _fc(monkeypatch, 'guest_merge')
    fc.sr_login_as_guest(sim_type)
    d = fc.sr_post(
        'listSimulations',
        {'simulationType': sim_type},
    )
    pkeq(1, len(d), 'expecting only one simulation: data={}', d)
    d = d[0].simulation
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
    r = fc.sr_get('authGithubLogin', {'simulation_type': sim_type})
    state = oc.values.state
    s = fc.sr_auth_state(isLoggedIn=True, method='guest')
    fc.sr_get('authGithubAuthorized', query={'state': state})
    fc.sr_auth_state(method='github', uid=guest_uid)
    fc.sr_post(
        'authCompleteRegistration',
        {
            'displayName': 'github user',
            'simulationType': sim_type,
        },
    )
    d = fc.sr_sim_data(sim_type=sim_type)
    d = fc.sr_post(
        'copySimulation',
        dict(
            simulationId=d.models.simulation.simulationId,
            simulationType=sim_type,
            name='oauth-sim',
            folder='/',
        ),
    )
    fc.sr_get('authLogout', {'simulation_type': sim_type})
    fc.sr_get('authGithubLogin', {'simulation_type': sim_type})
    state = oc.values.state
    fc.sr_get('authGithubAuthorized', query={'state': state})
    d = fc.sr_post(
        'listSimulations',
        {'simulationType': sim_type},
    )
    pkeq([u'Scooby Doo', u'guest-sim', u'oauth-sim'], sorted([x.name for x in d]))


def test_happy_path(monkeypatch):
    from pykern.pkdebug import pkdp
    from pykern import pkjson
    from pykern.pkunit import pkfail, pkok, pkeq, pkre, pkexcept

    fc, sim_type, oc = _fc(monkeypatch, 'happy')
    fc.sr_auth_state(isLoggedIn=False)
    r = fc.sr_get('authGithubLogin', {'simulation_type': sim_type}, redirect=False)
    pkeq(302, r.status_code)
    with pkexcept('SRException.*routeName=login'):
        d = fc.sr_post('listSimulations', {'simulationType': sim_type})
    state = oc.values.state
    pkre(state, r.headers['location'])
    fc.sr_auth_state(displayName=None, isLoggedIn=False, uid=None, userName=None)
    r = fc.sr_get('authGithubAuthorized', query={'state': state}, redirect=False)
    d = pkjson.load_any(r.data)
    pkeq(True, d.authState.isLoggedIn)
    with pkexcept('SRException.*routeName=completeRegistration'):
        fc.sr_post('listSimulations', {'simulationType': sim_type})
    fc.sr_post(
        'authCompleteRegistration',
        {
            'displayName': 'Happy Path',
            'simulationType': sim_type,
        },
    )
    s = fc.sr_auth_state(
        avatarUrl='https://avatars.githubusercontent.com/happy?size=40',
        displayName='Happy Path',
        isLoggedIn=True,
        userName='happy',
    )
    uid = s.uid
    r = fc.sr_get('authLogout', {'simulation_type': sim_type}, redirect=False)
    pkre('/{}$'.format(sim_type), r.headers['Location'])
    fc.sr_auth_state(
        avatarUrl=None,
        displayName=None,
        isLoggedIn=False,
        uid=uid,
        userName=None,
    )


def _fc(monkeypatch, user_name):
    from sirepo import srunit
    sim_type = 'myapp'
    fc = srunit.flask_client({
        'SIREPO_AUTH_METHODS': 'guest:github',
        'SIREPO_FEATURE_CONFIG_SIM_TYPES': sim_type,
        'SIREPO_AUTH_GITHUB_CALLBACK_URI': '/uri',
        'SIREPO_AUTH_GITHUB_KEY': 'key',
        'SIREPO_AUTH_GITHUB_SECRET': 'secret',
    })
    from sirepo import github_srunit
    from sirepo.auth import github

    fc.cookie_jar.clear()
    oc = github_srunit.MockOAuthClient(monkeypatch, user_name=user_name)
    return fc, sim_type, oc
