# -*- coding: utf-8 -*-
u"""?

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function

import re


def create_examples():
    """Adds missing app examples to all users.
    """
    from pykern import pkio
    from sirepo import feature_config
    from sirepo import server
    from sirepo import simulation_db
    from sirepo import cookie

    server.init()

    for d in pkio.sorted_glob(simulation_db.user_dir_name('*')):
        if _is_src_dir(d):
            continue;
        uid = simulation_db.uid_from_dir_name(d)
        cookie.init_mock(uid)
        for sim_type in feature_config.cfg.sim_types:
            simulation_db.verify_app_directory(sim_type)
            names = map(
                lambda x: x['name'],
                simulation_db.iterate_simulation_datafiles(sim_type, simulation_db.process_simulation_list, {
                    'simulation.isExample': True,
                }))
            for s in simulation_db.examples(sim_type):
                if s.models.simulation.name not in names:
                    simulation_db.save_new_example(s)


def purge_users(days=180, confirm=False):
    """Remove old users from db which have not registered.

    Args:
        days (int): maximum days of untouched files (old is mtime > days)
        confirm (bool): delete the directories if True (else don't delete) [False]

    Returns:
        list: directories removed (or to remove if confirm)
    """
    from pykern import pkio
    from sirepo import server
    from sirepo import simulation_db
    from sirepo import user_db
    from sirepo import user_state
    import datetime

    days = int(days)
    assert days >= 1, \
        '{}: days must be a positive integer'
    server.init()

    uids = []
    if user_state.login_module:
        uids = user_db.all_uids(user_state.login_module.UserModel)
    now = datetime.datetime.utcnow()
    to_remove = []
    for d in pkio.sorted_glob(simulation_db.user_dir_name('*')):
        if _is_src_dir(d):
            continue;
        if simulation_db.uid_from_dir_name(d) in uids:
            continue
        for f in pkio.walk_tree(d):
            if (now - now.fromtimestamp(f.mtime())).days <= days:
                break
        else:
            to_remove.append(d)
    if confirm:
        pkio.unchecked_remove(*to_remove)
    return to_remove


def _is_src_dir(d):
    return re.search(r'/src$', str(d))
