# -*- coding: utf-8 -*-
u"""Test simulationSerial

:copyright: Copyright (c) 2016 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest
pytest.importorskip('srwl_bl')


def test_login_logout():
    from pykern import pkconfig
    from pykern.pkunit import pkfail, pkok
    from sirepo import srunit
    import re

    fc = srunit.flask_client({
        'SIREPO_FEATURE_CONFIG_API_MODULES': 'oauth',
        'SIREPO_OAUTH_GITHUB_KEY': 'n/a',
        'SIREPO_OAUTH_GITHUB_SECRET': 'n/a',
        'SIREPO_OAUTH_GITHUB_CALLBACK_URI': 'n/a',
    })
    sim_type = 'srw'
    fc.get('/{}'.format(sim_type))
    text = fc.sr_get(
        'oauthLogin',
        {
            'simulation_type': sim_type,
            'oauth_type': 'github',
        },
        raw_response=True,
    ).data
    state = re.search(r'state=(.*?)"', text).group(1)
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
