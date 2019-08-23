# -*- coding: utf-8 -*-
u"""?

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function

import re
from pykern import pkio
from sirepo import auth
from sirepo import auth_db
from sirepo import feature_config
from sirepo import server
from sirepo import simulation_db
from sirepo.template import template_common
import datetime


def create_examples():
    """Adds missing app examples to all users.
    """
    server.init()

    for d in pkio.sorted_glob(simulation_db.user_dir_name('*')):
        if _is_src_dir(d):
            continue;
        uid = simulation_db.uid_from_dir_name(d)
        auth.init_mock(uid)
        for sim_type in feature_config.cfg.sim_types:
            simulation_db.verify_app_directory(sim_type)
            names = map(
                lambda x: x['name'],
                simulation_db.iterate_simulation_datafiles(sim_type, simulation_db.process_simulation_list, {
                    'simulation.isExample': True,
                }))
            for example in simulation_db.examples(sim_type):
                if example.models.simulation.name not in names:
                    _create_example(example)


def purge_guest_users(days=180, confirm=False):
    """Remove old users from db which have not registered.

    Args:
        days (int): maximum days of untouched files (old is mtime > days)
        confirm (bool): delete the directories if True (else don't delete) [False]

    Returns:
        (list, list): dirs and uids of removed guest users (or to remove if confirm)
    """

    days = int(days)
    assert days >= 1, \
        '{}: days must be a positive integer'
    server.init()
    from sirepo import srtime

    guest_uids = auth.guest_uids()
    now = srtime.utc_now()
    dirs_and_uids = {}

    for d in pkio.sorted_glob(simulation_db.user_dir_name('*')):
        uid = simulation_db.uid_from_dir_name(d)
        if _is_src_dir(d):
            continue
        if uid not in guest_uids:
            continue
        for f in pkio.walk_tree(d):
            if (now - now.fromtimestamp(f.mtime())).days <= days:
                break
        else:

            dirs_and_uids[d] = uid
    if confirm:
        pkio.unchecked_remove(*dirs_and_uids.keys())
        auth_db.UserRegistration.delete_all_for_column_by_values('uid', dirs_and_uids.values())

    return dirs_and_uids


def _create_example(example):
    data = simulation_db.save_new_example(example)
    # ensure all datafiles for the new example exist in the sim lib dir
    for f in template_common.lib_files(data):
        if not f.exists():
            r = template_common.resource_dir(data.simulationType).join(f.basename)
            assert r.exists(), 'Example missing resource file: {}'.format(f)
            pkio.mkdir_parent_only(f)
            r.copy(f)


def _is_src_dir(d):
    return re.search(r'/src$', str(d))
