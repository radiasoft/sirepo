# -*- coding: utf-8 -*-
"""Test jupyterhublogin

:copyright: Copyright (c) 2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
import pytest
import os


def setup_module(module):
    os.environ.update(
        SIREPO_FEATURE_CONFIG_PROPRIETARY_SIM_TYPES="jupyterhublogin",
    )


def test_logout(auth_fc):
    # Clears third party (jupyterhub) cookies
    fc = auth_fc

    from pykern.pkdebug import pkdp
    from sirepo.pkcli import jupyterhublogin

    e = "a@b.c"
    fc.sr_email_login(e)
    jupyterhublogin.create_user(e, "foo")
    fc.sr_logout()
