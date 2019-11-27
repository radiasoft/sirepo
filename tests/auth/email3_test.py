# -*- coding: utf-8 -*-
u"""test oauth conversion

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest


# NOTE: Do not rename this file, because conftest keys off the name
#  to set the config for this test case.
#TODO(robnagler) figure out how to pass parameters conveniently
#   to fixtures.

def test_oauth_conversion_setup(auth_fc, monkeypatch):
    """Prepares data for auth conversion

    You need to run this as a test (no other cases), and then:
        rm -rf email_data
        mv email_work email_data

    Also grab the cookie output, and add it to test_oauth_conversion
    """
    fc = auth_fc

    from pykern import pkcollections
    from pykern.pkdebug import pkdlog
    from pykern.pkunit import pkok, pkre, pkeq
    from sirepo.auth import github
    from sirepo import github_srunit

    oc = github_srunit.MockOAuthClient(monkeypatch, 'emailer')
    fc.sr_get('authGithubLogin', {'simulation_type': fc.sr_sim_type}, redirect=False)
    t = fc.sr_auth_state(userName=None, isLoggedIn=False, method=None)
    state = oc.values.state
    r = fc.sr_get('authGithubAuthorized', query={'state': state})
    uid = fc.sr_auth_state(
        displayName=None,
        method='github',
        needCompleteRegistration=True,
        userName='emailer',
    ).uid
    fc.sr_get('authLogout', {'simulation_type': fc.sr_sim_type})
