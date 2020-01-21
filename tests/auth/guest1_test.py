# -*- coding: utf-8 -*-
u"""Test auth.guest

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from __future__ import absolute_import, division, print_function
import pytest


def test_happy_path(auth_fc):
    fc = auth_fc

    from pykern import pkconfig, pkunit, pkio
    from pykern.pkunit import pkok, pkre, pkeq
    from pykern.pkdebug import pkdp
    import re

    fc.sr_get('authGuestLogin', {'simulation_type': fc.sr_sim_type})
    fc.sr_post('listSimulations', {'simulationType': fc.sr_sim_type})
    fc.sr_auth_state(
        avatarUrl=None,
        displayName='Guest User',
        guestIsOnlyMethod=False,
        isGuestUser=True,
        isLoggedIn=True,
        isLoginExpired=False,
        method='guest',
        needCompleteRegistration=False,
        userName=None,
        visibleMethods=['email'],
    )


def test_timeout(auth_fc):
    fc = auth_fc

    from pykern import pkconfig, pkunit, pkio
    from pykern.pkunit import pkok, pkre, pkeq, pkexcept
    from pykern.pkdebug import pkdp
    import re

    r = fc.sr_get('authGuestLogin', {'simulation_type': fc.sr_sim_type}, redirect=False)
    pkeq(302, r.status_code)
    pkre(fc.sr_sim_type, r.headers['location'])
    fc.sr_post('listSimulations', {'simulationType': fc.sr_sim_type})
    fc.sr_auth_state(
        isGuestUser=True,
        isLoggedIn=True,
        isLoginExpired=False,
    )
    fc.sr_get_json('adjustTime', params={'days': '2'})
    fc.sr_auth_state(
        isGuestUser=True,
        isLoggedIn=True,
        isLoginExpired=True,
    )
    with pkexcept('SRException.*guest-expired'):
        fc.sr_post('listSimulations', {'simulationType': fc.sr_sim_type})
