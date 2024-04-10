# -*- coding: utf-8 -*-
"""JupyterHub tests

:copyright: Copyright (c) 2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
import pytest
import os


def setup_module(module):
    os.environ.update(
        SIREPO_FEATURE_CONFIG_PROPRIETARY_SIM_TYPES="jupyterhublogin",
        SIREPO_AUTH_ROLE_MODERATION_MODERATOR_EMAIL="x@x.x",
    )


def test_check_auth_jupyterhub(fc):
    fc.sr_login_as_guest()
    # user doesn't exist
    fc.sr_get("checkAuthJupyterHub").assert_success()
    # user does exist
    fc.sr_get("checkAuthJupyterHub").assert_success()


def test_jupyterhub_redirect(fc):
    fc.sr_get("redirectJupyterHub", redirect=False).assert_http_redirect("jupyterHub")


def test_logout(auth_fc):
    # Clears third party (jupyterhub) cookies
    fc = auth_fc

    from pykern.pkdebug import pkdp
    from sirepo.pkcli import jupyterhublogin

    e = "a@b.c"
    fc.sr_email_login(e)
    jupyterhublogin.create_user(e, "foo")
    fc.sr_logout()
