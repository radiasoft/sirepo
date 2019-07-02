# -*- coding: utf-8 -*-
"""Wrapper to run Warp VND/WARP from the command line.

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkio
from pykern.pkdebug import pkdp, pkdc
from sirepo import mpi
from sirepo import simulation_db
from sirepo.template import template_common
import h5py
import numpy as np
import sirepo.template.warpvnd as template


def run(cfg_dir):
    with pkio.save_chdir(cfg_dir):
        exec(_script(), locals(), locals())
        data = simulation_db.read_json(template_common.INPUT_BASE_NAME)
        if data['report'] == 'fieldReport':
            res = template.generate_field_report(data, cfg_dir)
            res['tof_expected'] = field_results.tof_expected
            res['steps_expected'] = field_results.steps_expected,
            res['e_cross'] = field_results.e_cross
        elif data['report'] == 'fieldComparisonReport':
            wp.step(template.COMPARISON_STEP_SIZE)
            res = template.generate_field_comparison_report(data, cfg_dir)
        else:
            raise RuntimeError('unknown report: {}'.format(data['report']))
    simulation_db.write_result(res)


def run_background(cfg_dir):
    """Run warpvnd in ``cfg_dir`` with mpi

    Args:
        cfg_dir (str): directory to run warpvnd in
    """
    with pkio.save_chdir(cfg_dir):
        #TODO(pjm): disable running with MPI for now
        # mpi.run_script(_script())
        exec(_script(), locals(), locals())
        simulation_db.write_result({})


def _script():
    return pkio.read_text(template_common.PARAMETERS_PYTHON_FILE)
