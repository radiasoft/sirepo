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
    "SIREPO_SMTP_FROM_EMAIL": "x@x.x",
    "SIREPO_SMTP_FROM_NAME": "x",
    "SIREPO_SMTP_PASSWORD": "x",
    "SIREPO_SMTP_SERVER": "dev",
    "SIREPO_SMTP_USER": "x",
    "SIREPO_AUTH_METHODS": "email:guest",
    "SIREPO_FEATURE_CONFIG_SIM_TYPES": _sim_type,
}


def test_migration():
    """See if user gets migrated"""
    from sirepo import srunit
    from pykern import pkconfig

    with srunit.quest_start(cfg=_cfg) as qcall:
        from pykern.pkunit import pkeq, pkok, pkexcept, work_dir
        from pykern.pkdebug import pkdp

        # deprecated methods raise Unauthorized, but still login
        with pkexcept("SRException.*deprecated"):
            qcall.auth.login(method="github", uid="jeTJR5G4")
        # verify logged in
        pkeq("jeTJR5G4", qcall.auth.user_if_logged_in("github"))
