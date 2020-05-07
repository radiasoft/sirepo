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
import sirepo.sim_data
import sirepo.template.flash as template
import subprocess


def run_background(cfg_dir):
    data = simulation_db.read_json(template_common.INPUT_BASE_NAME)
    mpi.run_program(
        [sirepo.sim_data.get_class(data).flash_exe_name(data)],
    )

def setup_dev():
    import requests
    import shutil
    import sirepo.pkcli.admin

    def _get_file(dest):
        if cfg.dev_depot_url.startswith(_FILE_PREFIX):
            _local_file(dest)
            return
        _remote_file(dest)

    def _local_file(dest):
        p = pkio.py_path(cfg.dev_depot_url.replace(_FILE_PREFIX, ''))
        f = pkio.walk_tree(p.dirname, p.basename)
        assert len(f) == 1, f'expecting only 1 file found {f}'
        shutil.copy(f[0], dest)

    def _remote_file(dest):
        r = requests.get('{}/{}'.format(cfg.dev_depot_url, dest.basename))
        r.raise_for_status()
        dest.write_binary(r.content)


    assert pkconfig.channel_in('dev'), \
        'Only to be used in dev. channel={}'.format(pkconfig.cfg.channel)

    _FILE_PREFIX = 'file://'
    t = 'flash'
    d = sirepo.pkcli.admin.proprietary_code_dir(t)
    pkio.mkdir_parent(d)
    s = sirepo.sim_data.get_class(t)
    _get_file(d.join(s.FLASH_RPM_FILENAME))


cfg = pkconfig.init(
    dev_depot_url=(
        'file:///home/vagrant/src/yum/fedora/29/x86_64/dev/rscode-flash',
        str,
        'where to get flash files when in dev'
    )
)
