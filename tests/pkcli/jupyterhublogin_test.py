# -*- coding: utf-8 -*-
u"""Test pkcli.jupyterhublogin operations

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import os
import pytest


def setup_module(module):
    os.environ.update(
        SIREPO_FEATURE_CONFIG_PROPRIETARY_SIM_TYPES='jupyterhublogin',
    )


def test_create_new_user(auth_fc):
    from pykern import pkunit
    from pykern.pkcollections import PKDict
    import sirepo.pkcli.jupyterhublogin
    import sirepo.srdb

    fc = auth_fc
    e = 'e-t@b.c'
    n = 'foo'
    r = PKDict(email=e, jupyterhub_user_name=e.split('@')[0])
    pkunit.pkeq(r, sirepo.pkcli.jupyterhublogin.create_user(e, n))
    # create_user is idempotent. Returns user_name if user already exists
    pkunit.pkeq(r, sirepo.pkcli.jupyterhublogin.create_user(e, n))
