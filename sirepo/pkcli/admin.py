# -*- coding: utf-8 -*-
u"""?

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function

from pykern import pkio, pkconfig
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp
from sirepo import auth
from sirepo import auth_db
from sirepo import feature_config
from sirepo import sim_data
from sirepo import simulation_db
from sirepo import srdb
from sirepo import util
from sirepo.template import template_common
import datetime
import glob
import json
import os.path
import re
import shutil


def audit_proprietary_lib_files(*uid):
    """Add/removes proprietary files based on a user's roles

    For example, add the FLASH proprietary files if user has the sim_type_flash role.

    Args:
        *uid: UID(s) of the user(s) to audit. If None, all users will be audited.
    """
    import sirepo.server

    sirepo.server.init()
    import sirepo.auth_db
    import sirepo.auth

    #TODO(robnagler) locking
    for u in uid or sirepo.auth_db.all_uids():
        sirepo.auth_db.audit_proprietary_lib_files(u)


def create_examples():
    """Adds missing app examples to all users.
    """
    import sirepo.server

    sirepo.server.init()
    for d in pkio.sorted_glob(simulation_db.user_path().join('*')):
        if _is_src_dir(d):
            continue;
        uid = simulation_db.uid_from_dir_name(d)
        with auth.set_user_outside_of_http_request(uid):
            for sim_type in feature_config.cfg().sim_types:
                simulation_db.verify_app_directory(sim_type)
                names = [x.name for x in simulation_db.iterate_simulation_datafiles(
                    sim_type, simulation_db.process_simulation_list, {
                        'simulation.isExample': True,
                    })]
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


def _create_example(example):
    simulation_db.save_new_example(example)


def _is_src_dir(d):
    return re.search(r'/src$', str(d))
