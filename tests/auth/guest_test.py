# -*- coding: utf-8 -*-
u"""Test auth.guest

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from __future__ import absolute_import, division, print_function
import pytest


def test_happy_path():
    fc, sim_type = _fc()

    from pykern import pkconfig, pkunit, pkio
    from pykern.pkunit import pkok, pkre, pkeq
    from pykern.pkdebug import pkdp
    import re

    fc.sr_get('authGuestLogin', {'simulation_type': sim_type})
    fc.sr_post('listSimulations', {'simulationType': sim_type})
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


def test_invalid_method():
    fc, sim_type = _fc()

    from pykern import pkconfig, pkunit, pkio
    from pykern.pkunit import pkok, pkre
    from pykern.pkdebug import pkdp
    import re

    r = fc.sr_get('authGuestLogin', {'simulation_type': sim_type})
    fc.sr_post('listSimulations', {'simulationType': sim_type})
    import sirepo.auth
    sirepo.auth.cfg.methods = set(['email'])
    sirepo.auth.cfg.deprecated_methods = set()
    sirepo.auth.non_guest_methods \
        = sirepo.auth.visible_methods = sirepo.auth.valid_methods = tuple(sirepo.auth.cfg.methods)
    del sirepo.auth._METHOD_MODULES['guest']
    fc.sr_auth_state(
        displayName=None,
        isLoggedIn=False,
        needCompleteRegistration=False,
        uid=None,
        userName=None,
    )


def test_timeout():
    fc, sim_type = _fc()

    from pykern import pkconfig, pkunit, pkio
    from pykern.pkunit import pkok, pkre, pkeq, pkexcept
    from pykern.pkdebug import pkdp
    import re

    r = fc.sr_get('authGuestLogin', {'simulation_type': sim_type}, redirect=False)
    pkeq(302, r.status_code)
    pkre(sim_type, r.headers['location'])
    fc.sr_post('listSimulations', {'simulationType': sim_type})
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
        fc.sr_post('listSimulations', {'simulationType': sim_type})


def _fc(guest_only=False):
    from pykern.pkdebug import pkdp
    from pykern.pkcollections import PKDict
    from sirepo import srunit

    sim_type = 'myapp'
    cfg = PKDict(
        SIREPO_AUTH_EMAIL_FROM_EMAIL='x',
        SIREPO_AUTH_EMAIL_FROM_NAME='x',
        SIREPO_AUTH_EMAIL_SMTP_PASSWORD='x',
        SIREPO_AUTH_EMAIL_SMTP_SERVER='dev',
        SIREPO_AUTH_EMAIL_SMTP_USER='x',
        SIREPO_AUTH_GUEST_EXPIRY_DAYS='1',
        SIREPO_AUTH_METHODS='guest' if guest_only else 'email:guest',
        SIREPO_FEATURE_CONFIG_SIM_TYPES=sim_type,
    )
    fc = srunit.flask_client(cfg=cfg)
    # set the sentinel
    fc.cookie_jar.clear()
    fc.sr_get_root(sim_type)
    return fc, sim_type
