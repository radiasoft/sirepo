# -*- coding: utf-8 -*-
"""Wrapper to run FLASH from the command line.

:copyright: Copyright (c) 2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkio
from pykern.pkdebug import pkdp, pkdc
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
    if not _SIM_DATA.sim_files_exist(data):
        s = _SIM_DATA.dot_local_path('src')
        t = s.join(data.models.simulation.flashType)
        subprocess.run(template.setup_command(data), cwd=s, check=True)
        subprocess.run(['make'], cwd=t, check=True)
        _SIM_DATA.flash_compilation_to_sim_file_basenames(data)
        for c, b in _SIM_DATA.flash_compilation_to_sim_file_basenames(data).items():
            _SIM_DATA.put_sim_file(
                t.join(c),
                b,
                data,
            )
        # Need to write_parameters again becasue setup_units has changed
        template.write_parameters(
            data,
            run_dir=cfg_dir,
            is_parallel=True,
        )
    e = _SIM_DATA.get_sim_file(
        _SIM_DATA.flash_exe_basename(data),
        data,
        is_exe=True,
    )
    mpi.run_program([e])
