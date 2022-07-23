# -*- coding: utf-8 -*-
"""Test auth_db

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from sirepo import srunit
import pytest


_sim_type = "myapp"
_cfg = {
    "SIREPO_AUTH_DEPRECATED_METHODS": "github",
    "SIREPO_SMTP_FROM_EMAIL": "x",
    "SIREPO_SMTP_FROM_NAME": "x",
    "SIREPO_SMTP_PASSWORD": "x",
    "SIREPO_SMTP_SERVER": "dev",
    "SIREPO_SMTP_USER": "x",
    "SIREPO_AUTH_GITHUB_CALLBACK_URI": "/uri",
    "SIREPO_AUTH_GITHUB_KEY": "key",
    "SIREPO_AUTH_GITHUB_SECRET": "secret",
    "SIREPO_AUTH_METHODS": "email:guest",
    "SIREPO_FEATURE_CONFIG_SIM_TYPES": _sim_type,
}


@srunit.wrap_in_request(cfg=_cfg, want_user=False)
def test_migration():
    """See if user gets migrated"""
    from pykern.pkunit import pkeq, pkok, pkexcept, work_dir
    from pykern.pkdebug import pkdp
    from sirepo import auth

    # deprecated methods raise Unauthorized, but still login
    with pkexcept("SRException.*deprecated"):
        auth.login(auth.github, uid="jeTJR5G4")
    # verify logged in
    pkeq("jeTJR5G4", auth.user_if_logged_in("github"))
    pkok(work_dir().join("db/auth.db").exists(), "auth.db does not exist")
