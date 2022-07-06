# -*- coding: utf-8 -*-
"""Test pkcli.admin

:copyright: Copyright (c) 2021 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest


_UID_IN_DB = "IYgnLlSy"

_UID_NOT_IN_DB = "notexist"


def setup_module(module):
    from sirepo import srunit
    import os

    srunit.setup_srdb_root()
    os.environ.update(
        SIREPO_FEATURE_CONFIG_PROPRIETARY_SIM_TYPES="jupyterhublogin",
    )


def test_delete_user():
    from pykern import pkunit
    from sirepo import auth
    from sirepo import auth_db
    from sirepo import simulation_db
    from sirepo.pkcli import admin
    from sirepo.sim_api import jupyterhublogin

    _init_db()
    with auth_db.session_and_lock():
        pkunit.pkeq(_UID_IN_DB, auth.unchecked_get_user(_UID_IN_DB))
    admin.delete_user(_UID_IN_DB)
    with auth_db.session_and_lock():
        _is_empty_table(jupyterhublogin.JupyterhubUser)
        _is_empty_table(auth_db.UserRegistration)
        _is_empty_table(auth_db.UserRoleInvite)
    _is_empty_dir(jupyterhublogin.cfg.user_db_root_d)
    _is_empty_dir(simulation_db.user_path())


def test_no_user():
    from sirepo.pkcli import admin

    _init_db()
    admin.delete_user(_UID_NOT_IN_DB)


def _init_db():
    from pykern import pkio
    from pykern import pkunit
    from sirepo import srdb

    pkio.unchecked_remove(srdb.root())
    pkunit.data_dir().join("db").copy(srdb.root())


def _is_empty(result):
    from pykern import pkunit

    pkunit.pkeq([], result)


def _is_empty_dir(path):
    from pykern import pkio

    _is_empty(pkio.sorted_glob(path.join("*")))


def _is_empty_table(table):
    _is_empty(table.search_all_by())
