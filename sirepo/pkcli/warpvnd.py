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
import numpy as np
import sirepo.template.warpvnd as template

_INVALID_VOLTAGE = 1e+50

def run(cfg_dir):
    with pkio.save_chdir(cfg_dir):
        exec(_script(), locals(), locals())
        data = simulation_db.read_json(template_common.INPUT_BASE_NAME)

        if data['report'] == 'fieldReport':
            grid = data['models']['simulationGrid']
            plate_spacing = grid['plate_spacing'] * 1e-6
            beam = data['models']['beam']
            radius = beam['x_radius'] * 1e-6
            values = potential[xl:xu, zl:zu]

            if _is_invalid_value(values[0][-1]):
                simulation_db.write_result({
                    'error': 'Results could not be calculated.\n\nThe Simulation Grid may require adjustments to the Grid Points and Channel Width.',
                });
            else:
                simulation_db.write_result({
                    'aspect_ratio': 6.0 / 14,
                    'x_range': [0, plate_spacing, len(values[0])],
                    'y_range': [- radius, radius, len(values)],
                    'x_label': 'z [m]',
                    'y_label': 'x [m]',
                    'title': 'ϕ Across Whole Domain',
                    'z_matrix': values.tolist(),
                    'frequency_title': 'Volts',
                })
        else:
            raise RuntimeError('unknown report: {}'.format(data['report']))


def run_background(cfg_dir):
    """Run warpvnd in ``cfg_dir`` with mpi

    Args:
        cfg_dir (str): directory to run warpvnd in
    """
    with pkio.save_chdir(cfg_dir):
        mpi.run_script(_script())
        simulation_db.write_result({})


def _is_invalid_value(v):
    return np.isnan(v) or abs(v) > _INVALID_VOLTAGE


def _script():
    return pkio.read_text(template_common.PARAMETERS_PYTHON_FILE)
