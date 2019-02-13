# -*- coding: utf-8 -*-
u"""Test sirepo.beaker_compat

:copyright: Copyright (c) 2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest


def test_different_email():
    fc, sim_type = _fc()

    from pykern import pkconfig, pkunit, pkio
    from pykern.pkunit import pkok, pkre
    from pykern.pkdebug import pkdp
    from sirepo import srunit
    import re

    r = fc.sr_post(
        'emailAuthLogin',
        {'email': 'a@b.c', 'simulationType': sim_type},
    )
    r = fc.get(r.url)
    t = fc.sr_get('userState', raw_response=True).data
    pkre('"loginSession": "logged_in"', t)
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
    pkre('"loginSession": "logged_out"', t)
    r = fc.sr_post(
        'emailAuthLogin',
        {'email': 'x@y.z', 'simulationType': sim_type},
    )
    r = fc.get(r.url)
    r = fc.sr_post(
        'emailAuthDisplayName',
        {'email': 'x@y.z', 'displayName': 'xyz'},
    )
    t = fc.sr_get('userState', raw_response=True).data
    pkre('"userName": "x@y.z"', t)
    pkre('"displayName": "xyz"', t)
    pkre('"loginSession": "logged_in"', t)
    m = re.search('"uid": "([^"]+)"', t)
    uid2 = m.group(1)
    pkok(uid != uid2, 'did not get a new uid={}', uid)


def test_happy_path():
    fc, sim_type = _fc()

    from pykern import pkconfig, pkunit, pkio
    from pykern.pkunit import pkok, pkre
    from pykern.pkdebug import pkdp
    from sirepo import srunit
    import re

    # login as a new user, not in db
    r = fc.sr_post(
        'emailAuthLogin',
        {'email': 'a@b.c', 'simulationType': sim_type},
    )
    r = fc.get(r.url)
    r = fc.sr_post(
        'emailAuthDisplayName',
        {'email': 'a@b.c', 'displayName': 'abc'},
    )
    r = fc.sr_post('listSimulations', {'simulationType': sim_type})
    t = fc.sr_get('userState', raw_response=True).data
    pkre('"userName": "a@b.c"', t)
    pkre('"displayName": "abc"', t)
    pkre('"loginSession": "logged_in"', t)
    m = re.search('"uid": "([^"]+)"', t)
    uid = m.group(1)
    r = fc.sr_get('logout', {'simulation_type': sim_type}, raw_response=True)
    pkre('/{}$'.format(sim_type), r.headers['Location'])
    t = fc.sr_get('userState', raw_response=True).data
    pkre('"uid": "{}"'.format(uid), t)
    pkre('"userName": null', t)
    pkre('"displayName": null', t)
    pkre('"loginSession": "logged_out"', t)


def test_token_reuse():
    fc, sim_type = _fc()

    from pykern import pkconfig, pkunit, pkio
    from pykern.pkunit import pkok, pkre
    from pykern.pkdebug import pkdp
    import re

    r = fc.sr_post(
        'emailAuthLogin',
        {'email': 'a@b.c', 'simulationType': sim_type},
    )
    login_url = r.url
    r = fc.get(r.url)
    t = fc.sr_get('userState', raw_response=True).data
    pkre('"userName": "a@b.c"', t)
    r = fc.sr_get('logout', {'simulation_type': sim_type}, raw_response=True)
    r = fc.get(login_url)
    t = fc.sr_get('userState', raw_response=True).data
    pkre('"loginSession": "logged_out"', t)


def _fc():
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
    fc.get('/{}'.format(sim_type))
    return fc, sim_type

#todo email of a different user already logged in
#todo email and same email
#todo change email
#todo forgot email(?)
