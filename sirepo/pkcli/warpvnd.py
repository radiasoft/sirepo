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

_COMPARISON_STEP_SIZE = 100
_COMPARISON_FILE = 'diags/fields/electric/data00{}.h5'.format(_COMPARISON_STEP_SIZE)


def run(cfg_dir):
    with pkio.save_chdir(cfg_dir):
        exec(_script(), locals(), locals())
        data = simulation_db.read_json(template_common.INPUT_BASE_NAME)

        if data['report'] == 'fieldReport':
            values = potential[xl:xu, zl:zu]
            res = _generate_field_report(data, values, {
                'tof_expected': tof_expected,
                'steps_expected': steps_expected,
                'e_cross': e_cross,
            })
        elif data['report'] == 'fieldComparisonReport':
            step(_COMPARISON_STEP_SIZE)
            res = _generate_field_comparison_report(data)
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


def _create_plots(dimension, data, values, x_range):
    params = data['models']['fieldComparisonReport']
    y_range = None
    visited = {}
    plots = []
    #TODO(pjm): keep in sync with warpvnd.js cell colors
    color = ['red', 'green', 'blue']
    max_index = values.shape[1] if dimension == 'x' else values.shape[0]
    x_points = np.linspace(x_range[0], x_range[1], values.shape[1] if dimension == 'x' else values.shape[0])
    for i in (1, 2, 3):
        f = '{}Cell{}'.format('z' if dimension == 'x' else 'x', i)
        index = params[f]
        if index >= max_index:
            index = max_index - 1
        if index in visited:
            continue
        visited[index] = True
        if dimension == 'x':
            points = values[:, index].tolist()
        else:
            points = values[index, :].tolist()
        if dimension == 'x':
            pos = u'{:.3f} µm'.format(x_points[index] * 1e6)
        else:
            pos = '{:.0f} nm'.format(x_points[index] * 1e9)
        plots.append({
            'points': points,
            'color': color[i - 1],
            'label': u'{} Location {}'.format('Z' if dimension == 'x' else 'X', pos),
        })
        if y_range:
            y_range[0] = min(y_range[0], min(points))
            y_range[1] = max(y_range[1], max(points))
        else:
            y_range = [min(points), max(points)]
    return plots, y_range


def _generate_field_comparison_report(data):
    params = data['models']['fieldComparisonReport']
    dimension = params['dimension']
    with h5py.File(_COMPARISON_FILE) as f:
        values = f['data/{}/meshes/E/{}'.format(_COMPARISON_STEP_SIZE, dimension)]
        values = values[:, 0, :]
    radius = data['models']['simulationGrid']['channel_width'] / 2. * 1e-6
    x_range = [-radius, radius]
    z_range = [0, data['models']['simulationGrid']['plate_spacing'] * 1e-6]
    plots, y_range = _create_plots(dimension, data, values, z_range if dimension == 'x' else x_range)
    plot_range = x_range if dimension == 'x' else z_range
    return {
        'title': 'Comparison of E {}'.format(dimension),
        'y_label': 'E {} [V/m]'.format(dimension),
        'x_label': '{} [m]'.format(dimension),
        'y_range': y_range,
        'x_range': [plot_range[0], plot_range[1], len(plots[0]['points'])],
        'plots': plots,
    }


def _generate_field_report(data, values, res):
    grid = data['models']['simulationGrid']
    plate_spacing = grid['plate_spacing'] * 1e-6
    beam = data['models']['beam']
    radius = grid['channel_width'] / 2. * 1e-6

    if np.isnan(values).any():
        return {
            'error': 'Results could not be calculated.\n\nThe Simulation Grid may require adjustments to the Grid Points and Channel Width.',
        }
    return {
        'aspect_ratio': 6.0 / 14,
        'x_range': [0, plate_spacing, len(values[0])],
        'y_range': [- radius, radius, len(values)],
        'x_label': 'z [m]',
        'y_label': 'x [m]',
        'title': 'ϕ Across Whole Domain',
        'z_matrix': values.tolist(),
        'frequency_title': 'Volts',
        'tof_expected': res['tof_expected'],
        'steps_expected': res['steps_expected'],
        'e_cross': res['e_cross'],
    }


def _script():
    return pkio.read_text(template_common.PARAMETERS_PYTHON_FILE)
