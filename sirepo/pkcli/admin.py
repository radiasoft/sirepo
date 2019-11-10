# -*- coding: utf-8 -*-
u"""?

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function

from pykern import pkio
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp
from sirepo import auth
from sirepo import auth_db
from sirepo import feature_config
from sirepo import server
from sirepo import simulation_db
from sirepo.template import template_common
import datetime
import glob
import json
import os.path
import re
import shutil


def create_examples():
    """Adds missing app examples to all users.
    """
    server.init()

    for d in pkio.sorted_glob(simulation_db.user_dir_name().join('*')):
        if _is_src_dir(d):
            continue;
        uid = simulation_db.uid_from_dir_name(d)
        auth.init_mock(uid)
        for sim_type in feature_config.cfg().sim_types:
            simulation_db.verify_app_directory(sim_type)
            names = map(
                lambda x: x['name'],
                simulation_db.iterate_simulation_datafiles(sim_type, simulation_db.process_simulation_list, {
                    'simulation.isExample': True,
                }))
            for example in simulation_db.examples(sim_type):
                if example.models.simulation.name not in names:
                    _create_example(example)


def move_user_sims(target_uid=''):
    """Moves non-example sims and lib files into the target user's directory.
    Must be run in the source uid directory."""
    assert target_uid, 'missing target_uid'
    assert os.path.exists('srw/lib'), 'must run in user dir'
    assert os.path.exists('../{}'.format(target_uid)), 'missing target user dir: ../{}'.format(target_uid)
    sim_dirs = []
    lib_files = []

    for path in glob.glob('*/*/sirepo-data.json'):
        with open(path) as f:
            data = json.loads(f.read())
        sim = data['models']['simulation']
        if 'isExample' in sim and sim['isExample']:
            continue
        sim_dirs.append(os.path.dirname(path))

    for path in glob.glob('*/lib/*'):
        lib_files.append(path)

    for sim_dir in sim_dirs:
        target = '../{}/{}'.format(target_uid, sim_dir)
        assert not os.path.exists(target), 'target sim already exists: {}'.format(target)
        pkdlog(sim_dir)
        shutil.move(sim_dir, target)

    for lib_file in lib_files:
        target = '../{}/{}'.format(target_uid, lib_file)
        if os.path.exists(target):
            continue
        pkdlog(lib_file)
        shutil.move(lib_file, target)


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

    for d in pkio.sorted_glob(simulation_db.user_dir_name().join('*')):
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
    simulation_db.save_new_example(example)


def _is_src_dir(d):
    return re.search(r'/src$', str(d))
