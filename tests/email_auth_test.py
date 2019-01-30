# -*- coding: utf-8 -*-
u"""Test sirepo.beaker_compat

:copyright: Copyright (c) 2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest


def test_happy_path():
    from pykern import pkconfig, pkunit, pkio
    from pykern.pkunit import pkok
    from pykern.pkdebug import pkdp
    from sirepo import srunit

    sim_type = 'myapp'
    fc = srunit.flask_client(
        cfg={
            'SIREPO_EMAIL_AUTH_FROM_EMAIL': 'x',
            'SIREPO_EMAIL_AUTH_FROM_NAME': 'x',
            'SIREPO_EMAIL_AUTH_SMTP_PASSWORD': 'x',
            'SIREPO_EMAIL_AUTH_SMTP_SERVER': 'dev',
            'SIREPO_EMAIL_AUTH_SMTP_USER': 'x',
            'SIREPO_FEATURE_CONFIG_API_MODULES': 'email_auth',
            'SIREPO_FEATURE_CONFIG_SIM_TYPES': sim_type,
        },
    )
    r = fc.get('/{}'.format(sim_type))
    # Needed to create a user
    r = fc.sr_post('listSimulations', {'simulationType': sim_type})
    r = fc.sr_post(
        'emailAuthLogin',
        {'email': 'a@b.c', 'simulationType': sim_type},
    )
    r = fc.get(r.url);
    r = fc.sr_post(
        'emailAuthDisplayName',
        {'email': 'a@b.c', 'displayName': 'abc'},
    )
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

#todo email of a different user already logged in
#todo email and same email
#todo change email
#todo forgot email(?)
