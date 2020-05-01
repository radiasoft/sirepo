# -*- coding: utf-8 -*-
"""Wrapper to run FLASH from the command line.

:copyright: Copyright (c) 2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkconfig
from pykern import pkio
from pykern.pkdebug import pkdp, pkdc
from sirepo import mpi
from sirepo import simulation_db
from sirepo.template import template_common
import py.path
import sirepo.template.flash as template
import subprocess

EXE_NAME = 'flash4'

def run_background(cfg_dir):
    data = simulation_db.read_json(template_common.INPUT_BASE_NAME)
    mpi.run_program(
        [pkio.py_path(cfg_dir).join(EXE_NAME)],
    )

def setup_dev():
    import requests
    import shutil
    import sirepo.pkcli.admin
    import sirepo.sim_data

    def _get_file(dest):
        if cfg.dev_depot_url.startswith(_FILE_PREFIX):
            _local_file(dest)
            return
        _remote_file(dest)

    def _local_file(dest):
       shutil.copy(pkio.py_path(
           cfg.dev_depot_url.replace(_FILE_PREFIX, ''),
       ).join(dest.basename), dest)

    def _remote_file(dest):
        r = requests.get('{}/{}'.format(cfg.dev_depot_url, dest.basename))
        r.raise_for_status()
        dest.write_binary(r.content)


    assert pkconfig.channel_in('dev'), \
        'Only to be used in dev. channel={}'.format(pkconfig.cfg.channel)

    _FILE_PREFIX = 'file://'
    t = 'flash'
    d = sirepo.pkcli.admin.proprietary_sim_type_dir(t)
    s = sirepo.sim_data.get_class(t)
    for e in simulation_db.examples(t):
        _get_file(d.join(s.proprietary_lib_file_basename(e)))


cfg = pkconfig.init(
    dev_depot_url=(
        # TODO(e-carlin): This should be radiasoft.depot.org
        'file:///home/vagrant/src/FLASH4.6.2',
        str,
        'where to get flash files when in dev'
    )
)
