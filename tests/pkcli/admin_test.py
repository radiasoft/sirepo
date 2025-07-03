"""Test pkcli.admin

:copyright: Copyright (c) 2021 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

_UID_IN_DB = "IYgnLlSy"

_UID_NOT_IN_DB = "notexist"


def setup_module(module):
    from sirepo import srunit
    import os

    srunit.setup_srdb_root()
    os.environ.update(
        SIREPO_FEATURE_CONFIG_PROPRIETARY_SIM_TYPES="jupyterhublogin",
        SIREPO_AUTH_METHODS="email:guest",
    )


def test_create_user():
    from pykern import pkunit
    from sirepo.pkcli import admin, roles

    _init_db()
    pkunit.pkok(admin.create_user("a@a.a", "a"), "unable to create user")
    pkunit.pkok(admin.create_user("b@a.a", "b", plan="trial"), "unable to create user")
    pkunit.pkeq(
        [
            {"role": "premium", "expiration": None},
            {"role": "trial", "expiration": None},
            {"role": "user", "expiration": None},
        ],
        roles.list_with_expiration("b@a.a"),
    )


def test_delete_user():
    from pykern import pkunit
    from sirepo import simulation_db, srunit
    from sirepo.pkcli import admin
    from sirepo.sim_api import jupyterhublogin

    _init_db()
    with srunit.quest_start() as qcall:
        pkunit.pkeq(_UID_IN_DB, qcall.auth.unchecked_get_user(_UID_IN_DB))
    admin.delete_user(_UID_IN_DB)
    with srunit.quest_start() as qcall:
        for t in ("JupyterhubUser", "UserRegistration", "UserRoleModeration"):
            pkunit.pkeq(
                None,
                qcall.auth_db.model(t).unchecked_search_by(uid=_UID_IN_DB),
            )
    _is_empty_dir(jupyterhublogin.cfg().user_db_root_d)
    _is_empty_dir(simulation_db.user_path_root())


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
