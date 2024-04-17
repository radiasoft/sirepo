# -*- coding: utf-8 -*-
"""Database upgrade management

:copyright: Copyright (c) 2021-2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern import pkinspect, pkio
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdlog, pkdexc
import contextlib
import shutil
import sirepo.auth_db
import sirepo.auth_role
import sirepo.file_lock
import sirepo.job
import sirepo.quest
import sirepo.sim_data
import sirepo.simulation_db
import sirepo.srdb
import sirepo.srtime
import sirepo.template
import sirepo.util

#: checked before running upgrade and raises if found
_PREVENT_DB_UPGRADE_FILE = "prevent-db-upgrade"


def do_all(qcall):
    def _new_functions():
        x = qcall.auth_db.model("DbUpgrade").search_all_for_column("name")
        y = pkinspect.module_functions("_2")
        return ((n, y[n]) for n in sorted(set(y.keys()) - set(x)))

    with sirepo.file_lock.FileLock(_db_upgrade_file_lock_path()):
        assert (
            not _prevent_db_upgrade_file().exists()
        ), f"prevent_db_upgrade_file={_prevent_db_upgrade_file()} found"

        for n, f in _new_functions():
            with _backup_db_and_prevent_upgrade_on_error():
                pkdlog("running upgrade {}", n)
                f(qcall=qcall)
                qcall.auth_db.model(
                    "DbUpgrade",
                    name=n,
                    created=sirepo.srtime.utc_now(),
                ).save()


def _20230203_drop_spa_session(qcall):
    qcall.auth_db.drop_table("session_t")
    qcall.auth_db.drop_table("spa_session_t")


def _20231120_deploy_flash_update(qcall):
    """Add proprietary lib files to existing FLASH users' lib dir"""
    if not sirepo.template.is_sim_type("flash"):
        return
    for u in qcall.auth_db.model("UserRole").uids_with_roles(
        (sirepo.auth_role.for_sim_type("flash"),)
    ):
        with qcall.auth.logged_in_user_set(u):
            # Remove the existing rpm
            pkio.unchecked_remove(
                sirepo.simulation_db.simulation_lib_dir(
                    "flash",
                    qcall=qcall,
                ).join("flash.rpm"),
            )
            # Add's the flash proprietary lib files (unpacks flash.tar.gz)
            sirepo.sim_data.audit_proprietary_lib_files(
                qcall=qcall,
                force=True,
                sim_types=set(("flash",)),
            )


def _20240322_remove_github_auth(qcall):
    qcall.auth_db.drop_table("auth_github_user_t")


@contextlib.contextmanager
def _backup_db_and_prevent_upgrade_on_error():
    b = sirepo.auth_db.db_filename() + ".bak"
    sirepo.auth_db.db_filename().copy(b)
    try:
        yield
        pkio.unchecked_remove(b)
    except Exception:
        pkdlog("original db={}", b)
        _prevent_db_upgrade_file().ensure()
        raise


def _db_upgrade_file_lock_path():
    return sirepo.srdb.root().join("db_upgrade_in_progress")


def _migrate_sim_type(old_sim_type, new_sim_type, qcall):
    # can't use simulation_dir (or simulation_lib_dir) because the old sim doesn't exist
    old_sim_dir = sirepo.simulation_db.user_path(qcall=qcall).join(old_sim_type)
    if not old_sim_dir.exists():
        return
    new_sim_dir = sirepo.simulation_db.simulation_dir(new_sim_type, qcall=qcall)
    new_lib_dir = sirepo.simulation_db.simulation_lib_dir(new_sim_type, qcall=qcall)
    for p in pkio.sorted_glob(old_sim_dir.join("lib").join("*")):
        shutil.copy2(p, new_lib_dir.join(p.basename))
    for p in pkio.sorted_glob(
        old_sim_dir.join("*", sirepo.simulation_db.SIMULATION_DATA_FILE)
    ):
        data = sirepo.simulation_db.read_json(p)
        sim = data.models.simulation
        if sim.get("isExample"):
            continue
        new_p = new_sim_dir.join(sirepo.simulation_db.sim_from_path(p)[0])
        if new_p.exists():
            continue
        pkio.mkdir_parent(new_p)
        shutil.copy2(p, new_p.join(sirepo.simulation_db.SIMULATION_DATA_FILE))


def _prevent_db_upgrade_file():
    return sirepo.srdb.root().join(_PREVENT_DB_UPGRADE_FILE)
