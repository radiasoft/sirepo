# -*- coding: utf-8 -*-
u"""test invalid method for guest

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest

def test_invalid_method(auth_fc):
    fc = auth_fc

    from pykern import pkconfig, pkunit, pkio
    from pykern.pkunit import pkok, pkre
    from pykern.pkdebug import pkdp
    import re

    r = fc.sr_get('authGuestLogin', {'simulation_type': fc.sr_sim_type})
    fc.sr_post('listSimulations', {'simulationType': fc.sr_sim_type})
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
