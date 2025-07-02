"""Application administration

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern import pkio, pkconfig
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp
from sirepo import feature_config
from sirepo import sim_data
from sirepo import simulation_db
from sirepo import srdb
from sirepo import srtime
from sirepo import util
from sirepo.template import template_common
import datetime
import glob
import json
import os.path
import re
import shutil
import sirepo.auth_role
import sirepo.const
import sirepo.quest


_MILLISECONDS_PER_MONTH = 30 * 24 * 60 * 60 * 1000
_MAXIMUM_SIM_AGE_IN_MONTHS = 6


def audit_proprietary_lib_files(*uid):
    """Add/removes proprietary files based on a user's roles

    For example, add the FLASH proprietary files if user has the sim_type_flash role.

    Args:
        *uid: UID(s) of the user(s) to audit. If None, all users will be audited.
    """
    with sirepo.quest.start() as qcall:
        for u in uid or qcall.auth_db.all_uids():
            with qcall.auth.logged_in_user_set(u):
                sim_data.audit_proprietary_lib_files(qcall=qcall)


def create_user(email, display_name, plan=sirepo.auth_role.ROLE_PLAN_BASIC):
    """Creates a new user account with the specified email, display name, and plan.

    This function initializes a new user in the system using the provided email and display name.
    Optionally, a user plan can be specified. If no plan is provided, the default is
    `sirepo.auth_role.ROLE_PLAN_BASIC`.

    Args:
        email (str): The email address associated with the new user.
        display_name (str): The display name to associate with the user.
        plan (str, optional): The user’s subscription or access level plan.
            Defaults to `sirepo.auth_role.ROLE_PLAN_BASIC`.

    Returns:
        str: the new user's UID
    """
    with sirepo.quest.start() as qcall:
        u = qcall.auth.create_user_from_email(email, display_name=display_name)
        if plan:
            qcall.auth_db.model("UserRole").add_plan(plan, u)
    return u


def db_upgrade():
    with sirepo.quest.start() as qcall:
        qcall.auth_db.create_or_upgrade()


def delete_user(uid_or_user_name):
    """Delete a user and all of their data across Sirepo and Jupyter

    This will delete information based on what is configured. So configure
    all service (jupyterhublogin, email, etc.) that may be relevant. Once
    this script runs all records are blown away from the db's so if you
    forget to configure something you will have to delete manually.

    Does nothing if `uid_or_user_name` does not exist.

    Args:
        uid_or_user_name (str): UID or email for user to delete
    """
    import sirepo.template

    with sirepo.quest.start() as qcall:
        if (u := qcall.auth.unchecked_get_user(uid_or_user_name)) is None:
            return
        with qcall.auth.logged_in_user_set(u):
            if sirepo.util.is_jupyter_enabled():
                from sirepo.sim_api import jupyterhublogin

                jupyterhublogin.delete_user_dir(qcall=qcall)
            simulation_db.delete_user(qcall=qcall)
        # This needs to be done last so we have access to the records in
        # previous steps.
        qcall.auth_db.delete_user(uid=u)


def create_examples():
    """Adds missing app examples to all users"""
    with sirepo.quest.start() as qcall:
        examples = _get_examples_by_type(qcall)
        for t, s in _iterate_sims_by_users(qcall, examples.keys()):
            for e in examples[t]:
                if e.models.simulation.name not in s[t].keys():
                    _create_example(qcall, e)


def move_user_sims(uid):
    """Moves non-example sims and lib files into the target user's directory.
    Must be run in the source uid directory."""
    if not os.path.exists("srw/lib"):
        pkcli.command_error("srw/lib does not exist; must run in user dir")
    if not os.path.exists("../{}".format(uid)):
        pkcli.command_error(f"missing user_dir=../{uid}")
    sim_dirs = []
    lib_files = []
    for path in glob.glob("*/*/sirepo-data.json"):
        with open(path) as f:
            data = json.loads(f.read())
        sim = data["models"]["simulation"]
        if "isExample" in sim and sim["isExample"]:
            continue
        sim_dirs.append(os.path.dirname(path))

    for path in glob.glob("*/lib/*"):
        lib_files.append(path)
    for sim_dir in sim_dirs:
        target = "../{}/{}".format(uid, sim_dir)
        assert not os.path.exists(target), "target sim already exists: {}".format(
            target
        )
        pkdlog(sim_dir)
        shutil.move(sim_dir, target)
    for lib_file in lib_files:
        target = "../{}/{}".format(uid, lib_file)
        if os.path.exists(target):
            continue
        pkdlog(lib_file)
        shutil.move(lib_file, target)


def reset_examples():
    """Resets examples which haven't been modified recently.
    Deletes user examples which have been removed from the example list.
    """
    with sirepo.quest.start() as qcall:
        e = _get_examples_by_type(qcall)
        for t, s in _iterate_sims_by_users(qcall, e.keys()):
            o = _build_ops(list(s[t].values()), t, e)
            _revert(qcall, o, e)
            _delete(qcall, o)


def _build_ops(simulations, sim_type, examples):
    ops = PKDict(delete=[], revert=[])
    n = set([x.models.simulation.name for x in examples[sim_type]])
    for sim in simulations:
        if sim.name not in n:
            ops.delete.append((sim, sim_type))
        elif _example_is_too_old(sim.simulation.lastModified):
            ops.revert.append((sim.name, sim_type))
            ops.delete.append((sim, sim_type))
    return ops


def _create_example(qcall, example):
    simulation_db.save_new_example(example, qcall=qcall)


def _delete(qcall, ops):
    for s, t in ops.delete:
        simulation_db.delete_simulation(t, s.simulationId, qcall=qcall)


def _example_is_too_old(last_modified):
    return (
        (srtime.utc_now_as_milliseconds() - last_modified) / _MILLISECONDS_PER_MONTH
    ) > _MAXIMUM_SIM_AGE_IN_MONTHS


def _get_example_by_name(name, sim_type, examples):
    for e in examples[sim_type]:
        if e.models.simulation.name == name:
            return e
    raise AssertionError(f"Failed to find example simulation with name={name}")


def _get_examples_by_type(qcall):
    return PKDict(
        {t: simulation_db.examples(t) for t in feature_config.cfg().sim_types}
    )


def _get_named_example_sims(qcall, all_sim_types):
    return PKDict(
        {
            t: PKDict(
                {
                    x.name: x
                    for x in simulation_db.iterate_simulation_datafiles(
                        t,
                        simulation_db.process_simulation_list,
                        {"simulation.isExample": True},
                        qcall=qcall,
                    )
                }
            )
            for t in all_sim_types
        }
    )


def _is_src_dir(d):
    return re.search(r"/src$", str(d))


def _iterate_sims_by_users(qcall, all_sim_types):
    for d in pkio.sorted_glob(simulation_db.user_path_root().join("*")):
        if _is_src_dir(d):
            continue
        with qcall.auth.logged_in_user_set(simulation_db.uid_from_dir_name(d)):
            s = _get_named_example_sims(
                qcall,
                [a for a in all_sim_types if d.join(a).exists()],
            )
            for t in s.keys():
                yield (t, s)


def _revert(qcall, ops, examples):
    for n, t in ops.revert:
        _create_example(qcall, _get_example_by_name(n, t, examples))
