# -*- coding: utf-8 -*-
u"""Test simulationSerial

:copyright: Copyright (c) 2016 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest

### write a test with email auth will requrie a sep file


def test_happy_path(monkeypatch):
    from pykern import pkcollections
    from pykern import pkconfig
    from pykern.pkdebug import pkdp
    from pykern.pkunit import pkfail, pkok, pkeq, pkre
    from sirepo import srunit
    import re

    sim_type = 'myapp'
    fc = srunit.flask_client({
        'SIREPO_FEATURE_CONFIG_API_MODULES': 'oauth',
        'SIREPO_FEATURE_CONFIG_SIM_TYPES': sim_type,
        'SIREPO_OAUTH_GITHUB_CALLBACK_URI': '/uri',
        'SIREPO_OAUTH_GITHUB_KEY': 'key',
        'SIREPO_OAUTH_GITHUB_SECRET': 'secret',
    })
    from sirepo import oauth
    oc = _OAuthClient()
    monkeypatch.setattr(oauth, '_oauth_client', oc)
    fc.get('/{}'.format(sim_type))
    fc.sr_get(
        'oauthLogin',
        {
            'simulation_type': sim_type,
            'oauth_type': oauth.DEFAULT_OAUTH_TYPE,
        },
        raw_response=True,
    )
    t = fc.sr_get('userState', raw_response=True).data
    pkre('"userName": null', t)
    pkre('"displayName": null', t)
    pkre('"uid": null', t)
    pkre('"loginSession": "anonymous"', t)
    state = oc.values.state
    fc.sr_get(
        'oauthAuthorized',
        {
            'oauth_type': oauth.DEFAULT_OAUTH_TYPE,
        },
        query=pkcollections.Dict(state=state),
        raw_response=True,
    )
    t = fc.sr_get('userState', raw_response=True).data
    pkre('"userName": "joeblow"', t)
    pkre('"displayName": "Joe Blow"', t)
    pkre('"loginSession": "logged_in"', t)
    m = re.search('"uid": "([^"]+)"', t)
    uid = m.group(1)
    r = fc.sr_get('logout', {'simulation_type': sim_type}, raw_response=True)
    pkre('/{}$'.format(sim_type), r.headers['Location'])
    t = fc.sr_get('userState', raw_response=True).data
    pkre('"uid": "{}"'.format(uid), t)
    pkre('"userName": null', t)
    pkre('"displayName": null', t)
    pkre('"loginSession": "logged_out"', t)


def test_anonymous_merge(monkeypatch):
    from pykern import pkcollections
    from pykern import pkconfig
    from pykern.pkdebug import pkdp
    from pykern.pkunit import pkfail, pkok, pkeq, pkre
    from sirepo import srunit
    import re

    sim_type = 'myapp'
    fc = srunit.flask_client({
        'SIREPO_FEATURE_CONFIG_API_MODULES': 'oauth',
        'SIREPO_FEATURE_CONFIG_SIM_TYPES': sim_type,
        'SIREPO_OAUTH_GITHUB_CALLBACK_URI': '/uri',
        'SIREPO_OAUTH_GITHUB_KEY': 'key',
        'SIREPO_OAUTH_GITHUB_SECRET': 'secret',
    })
    from sirepo import oauth
    oc = _OAuthClient()
    monkeypatch.setattr(oauth, '_oauth_client', oc)
    fc.get('/{}'.format(sim_type))
    fc.sr_get(
        'oauthLogin',
        {
            'simulation_type': sim_type,
            'oauth_type': oauth.DEFAULT_OAUTH_TYPE,
        },
        raw_response=True,
    )
    state = oc.values.state
    t = fc.sr_get('userState', raw_response=True).data
    fc.sr_get(
        'oauthAuthorized',
        {
            'oauth_type': oauth.DEFAULT_OAUTH_TYPE,
        },
        query=pkcollections.Dict(state=state),
        raw_response=True,
    )
    d = fc.sr_post(
        'listSimulations',
        {'simulationType': sim_type, 'search': {'simulationName': 'Scooby Doo'}},
    )
    d = d[0].simulation
    d = fc.sr_post(
        'copySimulation',
        dict(
            simulationId=d.simulationId,
            simulationType=sim_type,
            name='oauth-sim',
        ),
    )
    t = fc.sr_get('userState', raw_response=True).data
    m = re.search('"uid": "([^"]+)"', t)
    oauth_uid = m.group(1)
    fc.sr_get(
        'logout',
        {'simulation_type': sim_type},
        query={'anonymous': '1'},
        raw_response=True,
    )
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
            name='anon-sim',
        ),
    )
    t = fc.sr_get('userState', raw_response=True).data
    m = re.search('"uid": "([^"]+)"', t)
    anon_uid = m.group(1)
    pkok(anon_uid != oauth_uid, 'anon_uid == oauth_uid={}', oauth_uid)
    fc.sr_get(
        'oauthLogin',
        {
            'simulation_type': sim_type,
            'oauth_type': oauth.DEFAULT_OAUTH_TYPE,
        },
        raw_response=True,
    )
    state = oc.values.state
    t = fc.sr_get('userState', raw_response=True).data
    fc.sr_get(
        'oauthAuthorized',
        {
            'oauth_type': oauth.DEFAULT_OAUTH_TYPE,
        },
        query=pkcollections.Dict(state=state),
        raw_response=True,
    )
    d = fc.sr_post(
        'listSimulations',
        {'simulationType': sim_type},
    )
    pkeq([u'Scooby Doo', u'anon-sim', u'oauth-sim'], sorted([x.name for x in d]))


class _OAuthClient(object):

    def __init__(self, values=None):
        from pykern import pkcollections

        self.values = values or pkcollections.Dict(
            access_token='xyzzy',
            data=pkcollections.Dict(
                id='9999',
                name='Joe Blow',
                login='joeblow',
            ),
        )

    def __call__(self, *args, **kwargs):
        return self

    def authorize(self, callback, state):
        from sirepo import http_reply

        self.values.callback = callback
        self.values.state = state
        return http_reply.gen_json_ok()

    def authorized_response(self, *args, **kwargs):
        return self.values

    def get(self, *args, **kwargs):
        return self.values
