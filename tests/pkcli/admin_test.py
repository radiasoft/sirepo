# -*- coding: utf-8 -*-
u"""Test pkcli.admin

:copyright: Copyright (c) 2021 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import os
import pytest

def setup_module(module):
    from sirepo import srunit
    import os
    srunit.setup_srdb_root()
    os.environ.update(
        SIREPO_FEATURE_CONFIG_DEFAULT_PROPRIETARY_SIM_TYPES='jupyterhublogin',
    )


def test_no_user():
    import sirepo.pkcli.admin
    from pykern import pkunit
    u = 'xxx'
    with pkunit.pkexcept('.*no registered user with uid=' + u):
        sirepo.pkcli.admin.delete_user(u)


def test_delete_user():
    from pykern import pkio
    from pykern import pkunit
    from sirepo import auth_db
    from sirepo import simulation_db
    from sirepo import srunit
    from sirepo.sim_api import jupyterhublogin
    import sirepo.pkcli.admin
    import sirepo.srdb

    pkio.unchecked_remove(sirepo.srdb.root())
    pkunit.data_dir().join('db').copy(sirepo.srdb.root())
    sirepo.pkcli.admin.delete_user('IYgnLlSy')
    with auth_db.session_and_lock():
        _is_empty(jupyterhublogin.JupyterhubUser.search_all_by())
        _is_empty(auth_db.UserRegistration.search_all_by())
    _is_empty(pkio.sorted_glob(jupyterhublogin.cfg.user_db_root_d.join('*')))
    _is_empty(pkio.sorted_glob(simulation_db.user_path().join('*')))


def _is_empty(result):
    from pykern import pkunit

    pkunit.pkeq([], result)
