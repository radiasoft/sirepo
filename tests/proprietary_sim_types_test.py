# -*- coding: utf-8 -*-
u"""test proprietary_sim_types

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkcollections import PKDict
import os
import pytest


def setup_module(module):
    os.environ.update(
        SIREPO_FEATURE_CONFIG_PROPRIETARY_SIM_TYPES='myapp',
        SIREPO_FEATURE_CONFIG_SIM_TYPES='srw',
    )


def test_myapp(auth_fc):
    from pykern import pkunit
    from pykern.pkdebug import pkdlog, pkdexc, pkdp

    fc = auth_fc
    # POSIT: Guests get all roles
    fc.sr_get('authGuestLogin', {'simulation_type': fc.sr_sim_type})
    # no forbidden
    fc.sr_sim_data()
    fc.sr_logout()
    r = fc.sr_post('authEmailLogin', {'email': 'a@b.c', 'simulationType': fc.sr_sim_type})
    fc.sr_email_confirm(fc, r)
    fc.sr_post(
        'authCompleteRegistration',
        {
            'displayName': 'abc',
            'simulationType': fc.sr_sim_type,
        },
    )
    r = fc.sr_post('listSimulations', {'simulationType': fc.sr_sim_type}, raw_response=True)
    pkunit.pkeq(403, r.status_code)
    import sirepo.auth_db
    sirepo.auth_db.UserRole.add_roles(
        fc.sr_auth_state().uid,
        [sirepo.auth.role_for_sim_type(fc.sr_sim_type)],
    )
    r = fc.sr_run_sim(fc.sr_sim_data(), 'heightWeightReport')
    p = r.get('plots')
    pkunit.pkok(p, 'expecting truthy r.plots={}', p)
