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
            if len(potential.shape) == 2:
                values = potential[xl:xu, zl:zu]
            else:
                # 3d results
                pkdp('!AXES {}', data.models.fieldReport.orientation)
                phi_slice = data.models.fieldReport.slice
                axes = data.models.fieldReport.orientation
                grid = data.models.simulationGrid
                if axes == 'xz':
                    values = potential[
                                 xl:xu,
                                 _get_slice_index(phi_slice, -grid.channel_width / 2., 1e6 * dy, NUM_Y - 1),
                                 zl:zu
                             ]
                elif axes == 'xy':
                    values = potential[
                                xl:xu,
                                yl:yu,
                                _get_slice_index(phi_slice, 0., 1e6 * dy, NUM_Z - 1)
                             ]
                else:
                    values = potential[
                                _get_slice_index(phi_slice, 0., 1e6 * dy, NUM_X - 1),
                                yl:yu,
                                zl:zu
                             ]

                #values = potential[xl:xu, int(NUM_Y / 2), zl:zu]
            res = _generate_field_report(data, values, {
                'tof_expected': tof_expected,
                'steps_expected': steps_expected,
                'e_cross': e_cross,
            })
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


def _generate_field_report(data, values, res):
    grid = data['models']['simulationGrid']
    plate_spacing = grid['plate_spacing'] * 1e-6
    beam = data['models']['beam']
    radius = grid['channel_width'] / 2. * 1e-6
    height = grid['channel_height'] / 2. * 1e-6
    axes = data.models.fieldReport.orientation
    axes = axes if axes is not None else 'xz'
    slice = data.models.fieldReport.slice
    if axes == 'xz':
        xr = [0, plate_spacing, len(values[0])]
        yr = [- radius, radius, len(values)]
        xl = 'z [m]'
        yl = 'x [m]'
        ar = 6.0 / 14
        other_axis = 'y'
    elif axes == 'xy':
        xr = [- height, height, len(values[0])]
        yr = [- radius, radius, len(values)]
        xl = 'y [m]'
        yl = 'x [m]'
        ar = 1.0
        other_axis = 'z'
    else:
        xr = [0, plate_spacing, len(values[0])]
        yr = [- height, height, len(values)]
        xl = 'z [m]'
        yl = 'y [m]'
        ar = 6.0 / 14
        other_axis = 'x'

    if np.isnan(values).any():
        return {
            'error': 'Results could not be calculated.\n\nThe Simulation Grid may require adjustments to the Grid Points and Channel Width.',
        }
    return {
        'aspectRatio': ar,
        'x_range': xr,
        'y_range': yr,
        'x_label': xl,
        'y_label': yl,
        'title': 'ϕ Across Whole Domain ({} = {}µm)'.format(other_axis, slice),
        'z_matrix': values.tolist(),
        'frequency_title': 'Volts',
        'tof_expected': res['tof_expected'],
        'steps_expected': res['steps_expected'],
        'e_cross': res['e_cross'],
    }


def _get_slice_index(x, min_x, dx, max_index):
    ds = (x - min_x) / dx
    pkdp('!DS {} IX {} val {} min {} d {}', ds, min(max_index, max(0, int(round(ds)))), x, min_x, dx)
    return min(max_index, max(0, int(round(ds))))

def _script():
    return pkio.read_text(template_common.PARAMETERS_PYTHON_FILE)
