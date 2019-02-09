# -*- coding: utf-8 -*-
u"""Test sirepo.beaker_compat

:copyright: Copyright (c) 2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest


def test_happy_path():
    from pykern import pkconfig, pkunit, pkio
    from pykern.pkunit import pkok, pkre
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
    # set the sentinel
    r = fc.get('/{}'.format(sim_type))
    # login as a new user, not in db
    r = fc.sr_post(
        'emailAuthLogin',
        {'email': 'a@b.c', 'simulationType': sim_type},
    )
    r = fc.get(r.url);
    r = fc.sr_post(
        'emailAuthDisplayName',
        {'email': 'a@b.c', 'displayName': 'abc'},
    )
    r = fc.sr_post('listSimulations', {'simulationType': sim_type})
    t = fc.sr_get('userState', raw_response=True).data
    pkre('"userName": "a@b.c"', t)
    pkre('"displayName": "abc"', t)
    r = fc.sr_get('logout', {'simulation_type': sim_type}, raw_response=True)
    pkre('/{}$'.format(sim_type), r.headers['Location'])
    t = fc.sr_get('userState', raw_response=True).data
    pkre('"userName": null', t)
    pkre('"displayName": null', t)


def test_different_email():
    from pykern import pkconfig, pkunit, pkio
    from pykern.pkunit import pkok, pkre
    from pykern.pkdebug import pkdp
    from sirepo import srunit
    import re

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
    # set the sentinel
    r = fc.get('/{}'.format(sim_type))
    r = fc.sr_post(
        'emailAuthLogin',
        {'email': 'a@b.c', 'simulationType': sim_type},
    )
    r = fc.get(r.url);
    r = fc.sr_post(
        'emailAuthDisplayName',
        {'email': 'a@b.c', 'displayName': 'abc'},
    )
    t = fc.sr_get('userState', raw_response=True).data
    pkre('"userName": "a@b.c"', t)
    r = fc.sr_get('logout', {'simulation_type': sim_type}, raw_response=True)
    pkre('/{}$'.format(sim_type), r.headers['Location'])
    t = fc.sr_get('userState', raw_response=True).data
    m = re.search('"uid": "([^"]+)"', t)
    uid = m.group(1)
    pkre('"userName": null', t)
    r = fc.sr_post(
        'emailAuthLogin',
        {'email': 'x@y.z', 'simulationType': sim_type},
    )
    r = fc.get(r.url);
    r = fc.sr_post(
        'emailAuthDisplayName',
        {'email': 'x@y.z', 'displayName': 'xyz'},
    )
    t = fc.sr_get('userState', raw_response=True).data
    pkre('"userName": "x@y.z"', t)
    pkre('"displayName": "xyz"', t)
    m = re.search('"uid": "([^"]+)"', t)
    uid2 = m.group(1)
    assert uid != uid2

#todo email of a different user already logged in
#todo email and same email
#todo change email
#todo forgot email(?)
