# -*- coding: utf-8 -*-
u"""Test simulationSerial

:copyright: Copyright (c) 2016 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest
pytest.importorskip('srwl_bl')


def test_login_logout(monkeypatch):
    from pykern import pkcollections
    from pykern import pkconfig
    from pykern.pkdebug import pkdp
    from pykern.pkunit import pkfail, pkok, pkeq
    from sirepo import srunit
    import re

    fc = srunit.flask_client({
        'SIREPO_FEATURE_CONFIG_API_MODULES': 'oauth',
        'SIREPO_OAUTH_GITHUB_KEY': 'key',
        'SIREPO_OAUTH_GITHUB_SECRET': 'secret',
        'SIREPO_OAUTH_GITHUB_CALLBACK_URI': '/uri',
    })
    from sirepo import oauth
    oc = _OAuthClient(
        pkcollections.Dict(
            access_token='xyzzy',
            data=pkcollections.Dict(
                id='9999',
                name='Joe Blow',
                login='joeblow',
            ),
        ),
    )
    monkeypatch.setattr(oauth, '_oauth_client', oc)
    sim_type = 'srw'
    fc.get('/{}'.format(sim_type))
    fc.sr_get(
        'oauthLogin',
        {
            'simulation_type': sim_type,
            'oauth_type': 'github',
        },
        raw_response=True,
    )
    state = oc.values.state
    fc.sr_get(
        'oauthAuthorized',
        {
            'oauth_type': 'github',
        },
        query=pkcollections.Dict(state=state),
        raw_response=True,
    )
    pkdp(state)
    #TODO(pjm): causes a forbidden error due to missing variables, need to mock-up an oauth test type
    #TODO(robnagler) test passes without it. why does it pass with it, because
    # fc throws an exception, and taht should throw something bad back
    # text = fc.get('/oauth-authorized/github')
    text = fc.sr_get(
        'logout',
        {
            'simulation_type': sim_type,
        },
        raw_response=True,
    ).data
    pkok(
        text.find('Redirecting') > 0,
        'missing redirect',
    )
    pkok(
        text.find('"/{}"'.format(sim_type)) > 0,
        'missing redirect target',
    )


class _OAuthClient(object):

    def __init__(self, values):
        self.values = values

    def __call__(self, *args, **kwargs):
        from pykern.pkdebug import pkdp
        pkdp([args, kwargs])
        return self

    def authorize(self, callback, state):
        from sirepo import http_reply

        self.values.callback = callback
        self.values.state = state
        return http_reply.gen_json_ok()

    def authorized_response(self, *args, **kwargs):
        from pykern.pkdebug import pkdp
        pkdp([args, kwargs])
        return self.values

    def get(self, *args, **kwargs):
        from pykern.pkdebug import pkdp
        pkdp([args, kwargs])
        return self.values
