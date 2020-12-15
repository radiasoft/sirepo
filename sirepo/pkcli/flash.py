# -*- coding: utf-8 -*-
"""Wrapper to run FLASH from the command line.

:copyright: Copyright (c) 2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkio
from pykern.pkdebug import pkdp, pkdc, pkdlog
from sirepo import mpi
from sirepo import simulation_db
from sirepo.template import template_common
import sirepo.sim_data
import sirepo.template.flash as template
import subprocess

_SIM_DATA = sirepo.sim_data.get_class('flash')

def run_background(cfg_dir):
    cfg_dir = pkio.py_path(cfg_dir)
    data = simulation_db.read_json(template_common.INPUT_BASE_NAME)
    s = _SIM_DATA.local_src_path()

    e = _SIM_DATA.sim_file_basenames(data)
    assert len(e) == 1, \
        f'expecting only one file {e}'
    e = cfg_dir.join(e[0])
    if not e.exists():
        import shutil
        pkdlog('flash binary {} not found. Compiling', e)
        t = s.join(data.models.simulation.flashType)
        # TODO(e-carlin): pksubprocess? Doesn't support cwd so not using for now
        subprocess.run(template.setup_command(data), cwd=s)
        subprocess.run(['make'], cwd=t)
        # TODO(e-carlin): flash4 from somehwere. is sim_data._FLASH_PREFIX
        _SIM_DATA.sim_file_copy(t.join('flash4'), e.basename, data)
        _SIM_DATA.sim_files_to_run_dir(data, cfg_dir)
    mpi.run_program([e])
