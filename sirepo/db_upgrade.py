"""Database upgrade management

:copyright: Copyright (c) 2021-2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern import pkinspect, pkio, pkjson
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdlog, pkdexc
import contextlib
import datetime
import shutil
import sirepo.auth_db
import sirepo.auth_role
import sirepo.feature_config
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


def _20240507_cloudmc_to_openmc(qcall):
    for u in qcall.auth_db.all_uids():
        with qcall.auth.logged_in_user_set(u):
            _migrate_sim_type("cloudmc", "openmc", qcall, u)


def _20240524_add_role_user(qcall):
    if not qcall.auth_db.table_exists("user_role_invite_t"):
        return
    qcall.auth_db.execute_sql(
        """
        INSERT INTO user_role_moderation_t (uid, role, status, moderator_uid, last_updated)
        SELECT uid, role, status, moderator_uid, last_updated
        FROM user_role_invite_t
        """
    )
    qcall.auth_db.drop_table("user_role_invite_t")
    qcall.auth_db.execute_sql(
        f"""INSERT INTO user_role_t (uid, role, expiration)
        SELECT uid, '{sirepo.auth_role.ROLE_USER}', NULL from user_registration_t"""
    )


def _20250114_add_role_plan_trial(qcall):
    """Give all existing users a trial plan with expiration"""
    qcall.auth_db.execute_sql(
        """INSERT INTO user_role_t (uid, role, expiration)
        SELECT uid, :role, :expiration FROM user_registration_t""",
        PKDict(
            role=sirepo.auth_role.ROLE_PLAN_TRIAL,
            expiration=datetime.datetime.utcnow()
            + datetime.timedelta(
                days=sirepo.feature_config.cfg().trial_expiration_days
            ),
        ),
    )


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


def _migrate_sim_type(old_sim_type, new_sim_type, qcall, uid):
    # can't use simulation_dir (or simulation_lib_dir) because the old sim doesn't exist
    old_sim_dir = sirepo.simulation_db.user_path(qcall=qcall, uid=uid).join(
        old_sim_type
    )
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
        assert data.simulationType == old_sim_type
        data.simulationType = new_sim_type
        pkjson.dump_pretty(
            data, filename=new_p.join(sirepo.simulation_db.SIMULATION_DATA_FILE)
        )
    pkio.unchecked_remove(old_sim_dir)


def _prevent_db_upgrade_file():
    return sirepo.srdb.root().join(_PREVENT_DB_UPGRADE_FILE)
