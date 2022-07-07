# -*- coding: utf-8 -*-
u"""Test deprecated auth.guest

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from __future__ import absolute_import, division, print_function
import pytest


def test_deprecated():
    fc, sim_type = _fc(guest_deprecated=True)

    from pykern import pkconfig, pkunit, pkio, pkcompat
    from pykern.pkunit import pkok, pkre, pkeq
    from pykern.pkdebug import pkdp
    import re

    r = fc.sr_get('authGuestLogin', {'simulation_type': sim_type}, redirect=False)
    pkeq(302, r.status_code)
    pkre('guest/deprecated', pkcompat.from_bytes(r.data))


def _fc(guest_deprecated=False):
    from pykern.pkdebug import pkdp
    from pykern.pkcollections import PKDict
    from sirepo import srunit

    sim_type = 'myapp'
    cfg = PKDict(
        SIREPO_AUTH_DEPRECATED_METHODS='guest',
        SIREPO_SMTP_FROM_EMAIL='x',
        SIREPO_SMTP_FROM_NAME='x',
        SIREPO_SMTP_PASSWORD='x',
        SIREPO_SMTP_SERVER='dev',
        SIREPO_SMTP_USER='x',
        SIREPO_AUTH_GUEST_EXPIRY_DAYS='1',
        SIREPO_AUTH_METHODS='email',
        SIREPO_FEATURE_CONFIG_SIM_TYPES=sim_type,
    )
    fc = srunit.flask_client(cfg=cfg)
    # set the sentinel
    fc.cookie_jar.clear()
    fc.sr_get_root(sim_type)
    return fc, sim_type
