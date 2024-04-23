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


def test_parseparams(fc):
    # list user's roles
    # if contains jupyter, remove
    # call to checkAuthJupyterHub
    # expect some exception
    # chdeck that still doesnt have role
    # call to redirectJupyterHub
    # expect some exception
    # give user role
    # call checkAuthJupyterHub
    # expect reply ok with username
    # call redirectJupyterHub
    # expect redirect to jupyterhub
    pass


#    a = fc.sr_auth_state()
#    print(f"123456authstate={a} dir={dir(a)}")
#    pass
