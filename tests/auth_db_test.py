# -*- coding: utf-8 -*-
u"""Test auth_db

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from sirepo import srunit
import pytest


_sim_type = 'myapp'
_cfg = {
    'SIREPO_AUTH_DEPRECATED_METHODS': 'github',
    'SIREPO_AUTH_EMAIL_FROM_EMAIL': 'x',
    'SIREPO_AUTH_EMAIL_FROM_NAME': 'x',
    'SIREPO_AUTH_EMAIL_SMTP_PASSWORD': 'x',
    'SIREPO_AUTH_EMAIL_SMTP_SERVER': 'dev',
    'SIREPO_AUTH_EMAIL_SMTP_USER': 'x',
    'SIREPO_AUTH_GITHUB_CALLBACK_URI': '/uri',
    'SIREPO_AUTH_GITHUB_KEY': 'key',
    'SIREPO_AUTH_GITHUB_SECRET': 'secret',
    'SIREPO_AUTH_METHODS': 'email:guest',
    'SIREPO_FEATURE_CONFIG_SIM_TYPES': _sim_type,
}

@srunit.wrap_in_request(cfg=_cfg, want_cookie=True)
def test_migration():
    """See if user gets migrated"""
    from pykern.pkunit import pkeq, pkok, pkexcept, work_dir
    from pykern.pkdebug import pkdp
    from sirepo import auth

    # deprecated methods raise Unauthorized, but still login
    with pkexcept('UNAUTHORIZED'):
        auth.login(auth.github, uid='jeTJR5G4')
    # verify logged in
    pkeq('jeTJR5G4', auth.user_if_logged_in('github'))
    pkok(work_dir().join('db/auth.db').exists(), 'auth.db does not exist')
