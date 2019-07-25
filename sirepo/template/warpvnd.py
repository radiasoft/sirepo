# -*- coding: utf-8 -*-
u"""Warp VND/WARP execution template.

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from __future__ import absolute_import, division, print_function
from pykern import pkcollections
from pykern import pkio
from pykern.pkdebug import pkdc, pkdp, pkdlog
from rswarp.cathode import sources
from rswarp.utilities.file_utils import readparticles
from scipy import constants
from sirepo import simulation_db
from sirepo.template import template_common
import h5py
import numpy as np
import os.path
import py.path
import re


COMPARISON_STEP_SIZE = 100
SIM_TYPE = 'warpvnd'
WANT_BROWSER_FRAME_CACHE = True

_FIELD_ANIMATIONS = ['fieldCalcAnimation', 'fieldComparisonAnimation']
_FIELD_ESTIMATE_FILE = 'estimates.json'
_COMPARISON_FILE = 'diags/fields/electric/data00{}.h5'.format(COMPARISON_STEP_SIZE)
_CULL_PARTICLE_SLOPE = 1e-4
_DENSITY_FILE = 'density.h5'
_EGUN_CURRENT_FILE = 'egun-current.npy'
_EGUN_STATUS_FILE = 'egun-status.txt'
_OPTIMIZER_OUTPUT_FILE = 'opt.out'
_OPTIMIZER_RESULT_FILE = 'opt.json'
_OPTIMIZER_STATUS_FILE = 'opt-run.out'
_OPT_RESULT_INDEX = 3
_OPTIMIZE_PARAMETER_FILE = 'parameters-optimize.py'
_PARTICLE_FILE = 'particles.h5'
_PARTICLE_PERIOD = 100
_POTENTIAL_FILE = 'potential.h5'
_REPORT_STYLE_FIELDS = ['colorMap', 'notes', 'color', 'impactColorMap', 'axes', 'slice']
_SCHEMA = simulation_db.get_schema(SIM_TYPE)

def background_percent_complete(report, run_dir, is_running):
    if report == 'optimizerAnimation':
        return _optimizer_percent_complete(run_dir, is_running)
    return _simulation_percent_complete(report, run_dir, is_running)


def fixup_old_data(data):
    if 'optimizer' not in data['models'] or 'enabledFields' not in data['models']['optimizer']:
        data['models']['optimizer'] = {
            'constraints': [],
            'enabledFields': {},
            'fields': [],
        }
    for m in [
            'egunCurrentAnimation',
            'impactDensityAnimation',
            'optimizer',
            'optimizerAnimation',
            'optimizerStatus',
            'particle3d',
            'particleAnimation',
            'simulation',
            'simulationGrid',
            'fieldCalcAnimation',
            'fieldCalculationAnimation',
            'fieldComparisonAnimation',
            'fieldComparisonReport',
            'fieldReport',
    ]:
        if m not in data.models:
            data.models[m] = {}
        template_common.update_model_defaults(data.models[m], m, _SCHEMA, dynamic=_dynamic_defaults(data, m))
    if 'joinEvery' in data.models.particle3d:
        del data.models.particle3d['joinEvery']
    types = data.models.conductorTypes if 'conductorTypes' in data.models else {}
    for c in types:
        if c is None:
            continue
        if 'isConductor' not in c:
            c.isConductor = '1' if c.voltage > 0 else '0'
        template_common.update_model_defaults(c, c.type if 'type' in c else 'box', _SCHEMA)
    for c in data.models.conductors:
        template_common.update_model_defaults(c, 'conductorPosition', _SCHEMA)
    template_common.organize_example(data)


def generate_field_comparison_report(data, run_dir, args=None):
    params = args if args is not None else data['models']['fieldComparisonAnimation']
    grid = data['models']['simulationGrid']
    dimension = params['dimension']
    with h5py.File(str(py.path.local(run_dir).join(_COMPARISON_FILE))) as f:
        values = f['data/{}/meshes/E/{}'.format(COMPARISON_STEP_SIZE, dimension)]
        values = values[()]

    radius = _meters(data['models']['simulationGrid']['channel_width'] / 2.)
    half_height = _meters(grid['channel_height'] / 2.)
    ranges = {
        'x': [-radius, radius],
        'y': [-half_height, half_height],
        'z': [0, _meters(grid['plate_spacing'])]
    }
    plot_range = ranges[dimension]
    plots, plot_y_range = _create_plots(dimension, params, values, ranges)
    return {
        'title': 'Comparison of E {}'.format(dimension),
        'y_label': 'E {} [V/m]'.format(dimension),
        'x_label': '{} [m]'.format(dimension),
        'y_range': plot_y_range,
        'x_range': [plot_range[0], plot_range[1], len(plots[0]['points'])],
        'plots': plots,
    }


def generate_field_report(data, run_dir, args=None):

    grid = data.models.simulationGrid
    plate_spacing = grid.plate_spacing * 1e-6
    radius = grid.channel_width / 2. * 1e-6
    height = grid.channel_height / 2. * 1e-6

    dx = grid.channel_width / grid.num_x
    dy = grid.channel_height / grid.num_y
    dz = grid.plate_spacing / grid.num_z

    f = str(py.path.local(run_dir).join(_POTENTIAL_FILE))
    hf = h5py.File(f, 'r')
    potential = np.array(template_common.h5_to_dict(hf, path='potential'))
    hf.close()

    axes = args.axes if args is not None else data.models.fieldReport.axes
    axes = axes if _is_3D(data) else 'xz'
    axes = axes if axes is not None else 'xz'
    phi_slice = float(args.slice if args is not None else data.models.fieldReport.slice)

    if len(potential.shape) == 2:
        values = potential[:grid.num_x + 1, :grid.num_z + 1]
    else:
        # 3d results
        if axes == 'xz':
            values = potential[
                     :, _get_slice_index(phi_slice, -grid.channel_height/ 2., dy, grid.num_y - 1), :
                     ]
        elif axes == 'xy':
            values = potential[
                     :, :,_get_slice_index(phi_slice, 0., dz, grid.num_z - 1)
                     ]
        else:
            values = potential[
                     _get_slice_index(phi_slice, -grid.channel_width / 2., dx, grid.num_x - 1), :, :
                     ]

    other_axis = re.sub('[' + axes + ']', '', 'xyz')

    x_max = len(values[0])
    y_max = len(values)
    vals_equal = np.isclose(np.std(values), 0., atol=1e-9)
    if axes == 'xz':
        xr = [0, plate_spacing, x_max]
        yr = [- radius, radius, y_max]
        x_label = 'z [m]'
        y_label = 'x [m]'
        ar = 6.0 / 14
    elif axes == 'xy':
        xr = [- height, height, x_max]
        yr = [- radius, radius, y_max]
        x_label = 'y [m]'
        y_label = 'x [m]'
        ar = radius / height,
    else:
        xr = [0, plate_spacing, x_max]
        yr = [- height, height, y_max]
        x_label = 'z [m]'
        y_label = 'y [m]'
        ar = 6.0 / 14

    if np.isnan(values).any():
        return {
            'error': 'Results could not be calculated.\n\nThe Simulation Grid may require adjustments to the Grid Points and Channel Width.',
        }
    return {
        'aspectRatio': ar,
        'x_range': xr,
        'y_range': yr,
        'x_label': x_label,
        'y_label': y_label,
        'title': 'ϕ Across Whole Domain ({} = {}µm)'.format(other_axis, phi_slice),
        'z_matrix': values.tolist(),
        'global_min': np.min(potential) if vals_equal else None,
        'global_max': np.max(potential) if vals_equal else None,
        'frequency_title': 'Volts'
    }


# use concept of "runner" animation?
def get_animation_name(data):
    if data['modelName'] == 'optimizerAnimation':
        return data['modelName']
    if data['modelName'] in _FIELD_ANIMATIONS:
        return 'fieldCalculationAnimation'
    return 'animation'


def get_application_data(data):
    if data['method'] == 'compute_simulation_steps':
        field_file = simulation_db.simulation_dir(SIM_TYPE, data['simulationId']) \
            .join('fieldCalculationAnimation').join(_FIELD_ESTIMATE_FILE)
        if field_file.exists():
            res = simulation_db.read_json(field_file)
            if res and 'tof_expected' in res:
                return {
                    'timeOfFlight': res['tof_expected'],
                    'steps': res['steps_expected'],
                    'electronFraction': res['e_cross'] if 'e_cross' in res else 0,
                }
        return {}
    raise RuntimeError('unknown application data method: {}'.format(data['method']))


def get_data_file(run_dir, model, frame, **kwargs):
    if model == 'particleAnimation' or model == 'egunCurrentAnimation' or model == 'particle3d':
        filename = str(run_dir.join(_PARTICLE_FILE if model == 'particleAnimation' or model == 'particle3d' else _EGUN_CURRENT_FILE))
        with open(filename) as f:
            return os.path.basename(filename), f.read(), 'application/octet-stream'
    #TODO(pjm): consolidate with template/warp.py
    files = _h5_file_list(run_dir, model)
    #TODO(pjm): last client file may have been deleted on a canceled animation,
    # give the last available file instead.
    if len(files) < frame + 1:
        frame = -1
    filename = str(files[int(frame)])
    with open(filename) as f:
        return os.path.basename(filename), f.read(), 'application/octet-stream'


def get_zcurrent_new(particle_array, momenta, mesh, particle_weight, dz):
    """
    Find z-directed current on a per cell basis
    particle_array: z positions at a given step
    momenta: particle momenta at a given step in SI units
    mesh: Array of Mesh spacings
    particle_weight: Weight from Warp
    dz: Cell Size
    """
    current = np.zeros_like(mesh)
    velocity = constants.c * momenta / np.sqrt(momenta**2 + (constants.electron_mass * constants.c)**2) * particle_weight

    for index, zval in enumerate(particle_array):
        bucket = np.round(zval/dz) #value of the bucket/index in the current array
        current[int(bucket)] += velocity[index]

    return current * constants.elementary_charge / dz


def get_simulation_frame(run_dir, data, model_data):
    md = pkcollections.Dict(model_data)
    frame_index = int(data['frameIndex'])
    if data['modelName'] == 'currentAnimation':
        data_file = open_data_file(run_dir, data['modelName'], frame_index)
        return _extract_current(model_data, data_file)
    if data['modelName'] == 'fieldAnimation':
        args = template_common.parse_animation_args(data, {'': ['field', 'startTime']})
        data_file = open_data_file(run_dir, data['modelName'], frame_index)
        return _extract_field(args.field, model_data, data_file)
    if data['modelName'] == 'particleAnimation' or data['modelName'] == 'particle3d':
        args = template_common.parse_animation_args(data, {'': ['renderCount', 'startTime']})
        return _extract_particle(run_dir, model_data, int(args.renderCount))
    if data['modelName'] == 'egunCurrentAnimation':
        return _extract_egun_current(model_data, run_dir.join(_EGUN_CURRENT_FILE), frame_index)
    if data['modelName'] == 'impactDensityAnimation':
        return _extract_impact_density(run_dir, model_data)
    if data['modelName'] == 'optimizerAnimation':
        args = template_common.parse_animation_args(data, {'': ['x', 'y']})
        return _extract_optimization_results(run_dir, model_data, args)
    if data['modelName'] == 'fieldCalcAnimation':
        args = template_common.parse_animation_args(data, {'': _SCHEMA.animationArgs.fieldCalcAnimation})
        return generate_field_report(md, run_dir, args=args)
    if data['modelName'] == 'fieldComparisonAnimation':
        args = template_common.parse_animation_args(data, {'': _SCHEMA.animationArgs.fieldComparisonAnimation})
        return generate_field_comparison_report(md, run_dir, args=args)
    raise RuntimeError('{}: unknown simulation frame model'.format(data['modelName']))


def lib_files(data, source_lib):
    res = []
    for m in data.models.conductorTypes:
        if m.type == 'stl':
            res.append(template_common.lib_file_name('stl', 'file', m.file))
    return template_common.filename_to_path(res, source_lib)


def models_related_to_report(data):
    """What models are required for this data['report']

    Args:
        data (dict): simulation
    Returns:
        list: Named models, model fields or values (dict, list) that affect report
    """
    if data['report'] == 'animation' or data['report'] == 'optimizerAnimation':
        return []
    res = ['simulationGrid']
    res.append(_non_opt_fields_to_array(data.models.beam))
    for container in ('conductors', 'conductorTypes'):
        for m in data.models[container]:
            res.append(_non_opt_fields_to_array(m))
    res.append(template_common.report_fields(data, data['report'], _REPORT_STYLE_FIELDS))
    return res


def new_simulation(data, new_simulation_data):
    if 'conductorFile' in new_simulation_data:
        c_file = new_simulation_data.conductorFile
        if c_file:
            # verify somehow?
            data.models.simulation.conductorFile = c_file
            data.models.simulationGrid.simulation_mode = '3d'


def open_data_file(run_dir, model_name, file_index=None):
    """Opens data file_index'th in run_dir

    Args:
        run_dir (py.path): has subdir ``hdf5``
        file_index (int): which file to open (default: last one)

    Returns:
        OrderedMapping: various parameters
    """
    files = _h5_file_list(run_dir, model_name)
    res = pkcollections.OrderedMapping()
    res.num_frames = len(files)
    res.frame_index = res.num_frames - 1 if file_index is None else file_index
    res.filename = str(files[res.frame_index])
    res.iteration = int(re.search(r'data(\d+)', res.filename).group(1))
    return res


def prepare_output_file(run_dir, data):
    if data.report == 'fieldComparisonReport' or data.report == 'fieldReport':
        fn = simulation_db.json_filename(template_common.OUTPUT_BASE_NAME, run_dir)
        if fn.exists():
            fn.remove()
            if data.report == 'fieldComparisonReport':
                simulation_db.write_result(generate_field_comparison_report(data, run_dir), run_dir=run_dir)
            else:
                simulation_db.write_result(generate_field_report(data, run_dir), run_dir=run_dir)


def python_source_for_model(data, model):
    return _generate_parameters_file(data)[0]


def remove_last_frame(run_dir):
    for m in ('currentAnimation', 'fieldAnimation', 'fieldCalculationAnimation'):
        files = _h5_file_list(run_dir, m)
        if len(files) > 0:
            pkio.unchecked_remove(files[-1])


def write_parameters(data, run_dir, is_parallel):
    """Write the parameters file

    Args:
        data (dict): input
        run_dir (py.path): where to write
        is_parallel (bool): run in background?
    """
    txt, v = _generate_parameters_file(data)
    if v['isOptimize']:
        pkio.write_text(
            run_dir.join(_OPTIMIZE_PARAMETER_FILE),
            txt,
        )
        pkio.write_text(
            run_dir.join(template_common.PARAMETERS_PYTHON_FILE),
            _generate_optimizer_file(data, v),
        )
    else:
        pkio.write_text(
            run_dir.join(template_common.PARAMETERS_PYTHON_FILE),
            txt,
        )


def _add_margin(bounds):
    width = bounds[1] - bounds[0]
    if width:
        margin = width * 0.05
    else:
        margin = 0.05
    return [bounds[0] - margin, bounds[1] + margin]


def _add_particle_paths(electrons, x_points, y_points, z_points, half_height, limit):
    # adds paths for the particleAnimation report
    # culls adjacent path points with similar slope
    count = 0
    cull_count = 0
    for i in range(min(len(electrons[1]), limit)):
        res = {'x': [], 'y': [], 'z': []}
        num_points = len(electrons[1][i])
        prev = [None, None, None]
        for j in range(num_points):
            curr = [
                electrons[1][i][j],
                electrons[0][i][j],
                electrons[2][i][j],
            ]
            if j > 0 and j < num_points - 1:
                next = [
                    electrons[1][i][j+1],
                    electrons[0][i][j+1],
                    electrons[2][i][j+1]
                ]
                if _cull_particle_point(curr, next, prev):
                    cull_count += 1
                    continue
            res['x'].append(curr[0])
            res['y'].append(curr[1])
            res['z'].append(curr[2])
            prev = curr
        count += len(res['x'])
        x_points.append(res['x'])
        y_points.append(res['y'])
        z_points.append(res['z'])
    pkdc('particles: {} paths, {} points {} points culled', len(x_points), count, cull_count)


def _compute_delta_for_field(data, bounds, field):
    #TODO(pjm): centralize list of meter fields
    if field in ('xLength', 'yLength', 'zLength', 'xCenter', 'yCenter', 'zCenter'):
        bounds[0] = _meters(bounds[0])
        bounds[1] = _meters(bounds[1])
    delta = {
        'z': _grid_delta(data, 'plate_spacing', 'num_z'),
        'x': _grid_delta(data, 'channel_width', 'num_x'),
        'y': _grid_delta(data, 'channel_height', 'num_y'),
    }
    m = re.search(r'^(\w)Center$', field)
    if m:
        dim = m.group(1)
        bounds += [delta[dim], False]
        return;
    _DEFAULT_SIZE = data.models.optimizer.continuousFieldSteps
    res = (bounds[1] - bounds[0]) / _DEFAULT_SIZE
    bounds += [res if res else bounds[1], True]


def _create_plots(dimension, params, values, ranges):
    all_axes = 'xyz'
    other_axes = re.sub('[' + dimension + ']', '', all_axes)
    y_range = None
    plots = []
    color = _SCHEMA.constants.cellColors
    label_fmts = {
        'x': u'{:.0f} nm',
        'y': u'{:.0f} nm',
        'z': u'{:.3f} µm'
    }
    label_factors = {
        'x': 1e9,
        'y': 1e9,
        'z': 1e6
    }
    x_points = {}
    for axis_idx, axis in enumerate(all_axes):
        if axis not in other_axes:
            continue
        x_points[axis] = np.linspace(ranges[axis][0], ranges[axis][1], values.shape[axis_idx])
    for i in (1, 2, 3):
        other_indices = {}
        for axis_idx, axis in enumerate(all_axes):
            if axis not in other_axes:
                continue
            f = '{}Cell{}'.format(axis, i)
            index = int(params[f])
            max_index = values.shape[axis_idx]
            if index >= max_index:
                index = max_index - 1
            other_indices[axis] = index
        if dimension == 'x':
            points = values[:, other_indices['y'], other_indices['z']].tolist()
        elif dimension == 'y':
            points = values[other_indices['x'], :, other_indices['z']].tolist()
        else:
            points = values[other_indices['x'], other_indices['y'], :].tolist()

        label = ''
        for axis in other_indices:
            v = x_points[axis][other_indices[axis]]
            pos = label_fmts[axis].format(v * label_factors[axis])
            label = label + u'{} Location {} '.format(axis.upper(), pos)
        plots.append({
            'points': points,
            #TODO(pjm): refactor with template_common.compute_plot_color_and_range()
            'color': color[i - 1],
            'label': label
        })
        if y_range:
            y_range[0] = min(y_range[0], min(points))
            y_range[1] = max(y_range[1], max(points))
        else:
            y_range = [min(points), max(points)]
    return plots, y_range


def _cull_particle_point(curr, next, prev):
    # check all three dimensions xy, xz, yz
    if _particle_line_has_slope(curr, next, prev, 0, 1) \
       or _particle_line_has_slope(curr, next, prev, 0, 2) \
       or _particle_line_has_slope(curr, next, prev, 1, 2):
        return False
    return True


# defaults that depend on the current data
def _dynamic_defaults(data, model):
    if model == 'fieldComparisonAnimation' or model == 'fieldComparisonReport':
        grid = data.models.simulationGrid
        return {
            'dimension': 'x',
            'xCell1': 0,
            'xCell2': int(grid.num_x / 2.),
            'xCell3': grid.num_x,
            'yCell1': 0,
            'yCell2': int(grid.num_y / 2.) if _is_3D(data) else 0,
            'yCell3': grid.num_y if _is_3D(data) else 0,
            'zCell1': 0,
            'zCell2': int(grid.num_z / 2.),
            'zCell3': grid.num_z,
        }
    return None


def _extract_current(data, data_file):
    grid = data['models']['simulationGrid']
    plate_spacing = _meters(grid['plate_spacing'])
    dz = plate_spacing / grid['num_z']
    zmesh = np.linspace(0, plate_spacing, grid['num_z'] + 1) #holds the z-axis grid points in an array
    report_data = readparticles(data_file.filename)
    data_time = report_data['time']
    with h5py.File(data_file.filename, 'r') as f:
        weights = np.array(f['data/{}/particles/beam/weighting'.format(data_file.iteration)])
    curr = get_zcurrent_new(report_data['beam'][:,4], report_data['beam'][:,5], zmesh, weights, dz)
    return _extract_current_results(data, curr, data_time)


def _extract_current_results(data, curr, data_time):
    grid = data['models']['simulationGrid']
    plate_spacing = _meters(grid['plate_spacing'])
    zmesh = np.linspace(0, plate_spacing, grid['num_z'] + 1) #holds the z-axis grid points in an array
    beam = data['models']['beam']
    if _is_3D(data):
        cathode_area = _meters(grid['channel_width']) * _meters(grid['channel_height'])
    else:
        cathode_area = _meters(grid['channel_width'])
    RD_ideal = sources.j_rd(beam['cathode_temperature'], beam['cathode_work_function']) * cathode_area
    JCL_ideal = sources.cl_limit(beam['cathode_work_function'], beam['anode_work_function'], beam['anode_voltage'], plate_spacing) * cathode_area

    if beam['currentMode'] == '2' or (beam['currentMode'] == '1' and beam['beam_current'] >= JCL_ideal):
        curr2 = np.full_like(zmesh, JCL_ideal)
        y2_title = 'Child-Langmuir cold limit'
    else:
        curr2 = np.full_like(zmesh, RD_ideal)
        y2_title = 'Richardson-Dushman'
    return {
        'title': 'Current for Time: {:.4e}s'.format(data_time),
        'x_range': [0, plate_spacing],
        'y_label': 'Current [A]',
        'x_label': 'Z [m]',
        'points': [
            curr.tolist(),
            curr2.tolist(),
        ],
        'x_points': zmesh.tolist(),
        'y_range': [min(np.min(curr), np.min(curr2)), max(np.max(curr), np.max(curr2))],
        'y1_title': 'Current',
        'y2_title': y2_title,
    }


def _extract_egun_current(data, data_file, frame_index):
    v = np.load(str(data_file), allow_pickle=True)
    if frame_index >= len(v):
        frame_index = -1;
    # the first element in the array is the time, the rest are the current measurements
    return _extract_current_results(data, v[frame_index][1:], v[frame_index][0])


def _extract_field(field, data, data_file):
    grid = data['models']['simulationGrid']
    plate_spacing = _meters(grid['plate_spacing'])
    beam = data['models']['beam']
    radius = _meters(grid['channel_width'] / 2.)
    selector = field
    if not field == 'phi':
        selector = 'E/{}'.format(field)
    with h5py.File(data_file.filename, 'r') as f:
        values = np.array(f['data/{}/meshes/{}'.format(data_file.iteration, selector)])
        data_time = f['data/{}'.format(data_file.iteration)].attrs['time']
        dt = f['data/{}'.format(data_file.iteration)].attrs['dt']
    if field == 'phi':
        values = values[0,:,:]
        title = 'ϕ'
    else:
        values = values[:,0,:]
        title = 'E {}'.format(field)
    return {
        'x_range': [0, plate_spacing, len(values[0])],
        'y_range': [- radius, radius, len(values)],
        'x_label': 'z [m]',
        'y_label': 'x [m]',
        'title': '{} for Time: {:.4e}s, Step {}'.format(title, data_time, data_file.iteration),
        'aspectRatio': 6.0 / 14,
        'z_matrix': values.tolist(),
    }


def _extract_impact_density(run_dir, data):
    hf = h5py.File(str(run_dir.join(_DENSITY_FILE)), 'r')
    plot_info = template_common.h5_to_dict(hf, path='density')
    hf.close()
    if 'error' in plot_info:
        return plot_info
    #TODO(pjm): consolidate these parameters into one routine used by all reports
    grid = data.models.simulationGrid
    plate_spacing = _meters(grid.plate_spacing)
    radius = _meters(grid.channel_width / 2.)
    width = 0

    dx = plot_info['dx']
    dy = 0
    dz = plot_info['dz']

    if _is_3D(data):
        dy = 0 #plot_info['dy']
        width = _meters(grid.channel_width)

    gated_ids = plot_info['gated_ids'] if 'gated_ids' in plot_info else []
    lines = []

    for i in gated_ids:
        v = gated_ids[i]
        for pos in ('bottom', 'left', 'right', 'top'):
            if pos in v:
                zmin, zmax, xmin, xmax = v[pos]['limits']
                row = {
                    'density': v[pos]['density'].tolist(),
                }
                if pos in ('bottom', 'top'):
                    row['align'] = 'horizontal'
                    row['points'] = [zmin, zmax, xmin + dx / 2.]
                else:
                    row['align'] = 'vertical'
                    row['points'] = [xmin, xmax, zmin + dz / 2.]
                lines.append(row)

    return {
        'title': 'Impact Density',
        'x_range': [0, plate_spacing],
        'y_range': [-radius, radius],
        'z_range': [-width / 2., width / 2.],
        'y_label': 'x [m]',
        'x_label': 'z [m]',
        'z_label': 'y [m]',
        'density': plot_info['density'] if 'density' in plot_info else [],
        'density_lines': lines,
        'v_min': plot_info['min'],
        'v_max': plot_info['max'],
    }


def _extract_optimization_results(run_dir, data, args):
    x_index = int(args.x or '0')
    y_index = int(args.y or '0')
    # steps, time, tolerance, result, p1, ... pn
    res, best_row = _read_optimizer_output(run_dir)
    field_info = res[:,:4]
    field_values = res[:,4:]
    fields = data.models.optimizer.fields
    if x_index > len(fields) - 1:
        x_index = 0
    if y_index > len(fields) - 1:
        y_index = 0
    x = field_values[:, x_index]
    y = field_values[:, y_index]
    if x_index == y_index:
        y = np.zeros(len(y))
    score = field_info[:, _OPT_RESULT_INDEX]
    return {
        'title': '',
        'v_min': min(score),
        'v_max': max(score),
        'x_range': _add_margin([min(x), max(x)]),
        'y_range': _add_margin([min(y), max(y)]),
        'x_field': fields[x_index].field,
        'y_field': fields[y_index].field,
        'optimizerPoints': field_values.tolist(),
        'optimizerInfo': field_info.tolist(),
        'x_index': x_index,
        'y_index': y_index,
        'fields': map(lambda x: x.field, fields),
    }


def _extract_particle(run_dir, data, limit):
    hf = h5py.File(str(run_dir.join(_PARTICLE_FILE)), 'r')
    d = template_common.h5_to_dict(hf, 'particle')
    kept_electrons = d['kept']
    lost_electrons = d['lost']
    hf.close()
    grid = data['models']['simulationGrid']
    plate_spacing = _meters(grid['plate_spacing'])
    radius = _meters(grid['channel_width'] / 2.)
    half_height = grid['channel_height'] if 'channel_height' in grid else 5.
    half_height = _meters(half_height / 2.)
    x_points = []
    y_points = []
    z_points = []
    _add_particle_paths(kept_electrons, x_points, y_points, z_points, half_height, limit)
    lost_x = []
    lost_y = []
    lost_z = []
    _add_particle_paths(lost_electrons, lost_x, lost_y, lost_z, half_height, limit)
    return {
        'title': 'Particle Trace',
        'x_range': [0, plate_spacing],
        'y_label': 'x [m]',
        'x_label': 'z [m]',
        'z_label': 'y [m]',
        'points': y_points,
        'x_points': x_points,
        'z_points': z_points,
        'y_range': [-radius, radius],
        'z_range': [-half_height, half_height],
        'lost_x': lost_x,
        'lost_y': lost_y,
        'lost_z': lost_z
    }


def _find_by_id(container, id):
    for c in container:
        if str(c.id) == str(id):
            return c
    assert False, 'missing id: {} in container'.format(id)


def _get_slice_index(x, min_x, dx, max_index):
    return min(max_index, max(0, int(round((x - min_x) / dx))))


def _grid_delta(data, length_field, count_field):
    grid = data.models.simulationGrid
    #TODO(pjm): already converted to meters
    return grid[length_field] / grid[count_field]


def _generate_optimizer_file(data, v):
    # iterate opt vars and compute [min, max, dx, is_continuous]
    for opt in data.models.optimizer.fields:
        m, f, container, id = _parse_optimize_field(opt.field)
        opt.bounds = [opt.minimum, opt.maximum]
        _compute_delta_for_field(data, opt.bounds, f)
    v['optField'] = data.models.optimizer.fields
    v['optimizerStatusFile'] = _OPTIMIZER_STATUS_FILE
    v['optimizerOutputFile'] = _OPTIMIZER_OUTPUT_FILE
    v['optimizerResultFile'] = _OPTIMIZER_RESULT_FILE
    return _render_jinja('optimizer', v)


def _generate_parameters_file(data):
    v = None
    template_common.validate_models(data, _SCHEMA)
    res, v = template_common.generate_parameters_file(data)
    v['particlePeriod'] = _PARTICLE_PERIOD
    v['particleFile'] = _PARTICLE_FILE
    v['potentialFile'] = _POTENTIAL_FILE
    v['stepSize'] = COMPARISON_STEP_SIZE
    v['densityFile'] = _DENSITY_FILE
    v['egunCurrentFile'] = _EGUN_CURRENT_FILE
    v['estimateFile'] = _FIELD_ESTIMATE_FILE
    v['conductors'] = _prepare_conductors(data)
    v['usesSTL'] = any(ct['file'] is not None for ct in data.models.conductorTypes)
    v['maxConductorVoltage'] = _max_conductor_voltage(data)
    v['is3D'] = _is_3D(data)
    if not v['is3D']:
        v['simulationGrid_num_y'] = v['simulationGrid_num_x']
        v['simulationGrid_channel_height'] = v['simulationGrid_channel_width']
    if 'report' not in data:
        data['report'] = 'animation'
    v['isOptimize'] = data['report'] == 'optimizerAnimation'
    if v['isOptimize']:
        _replace_optimize_variables(data, v)
    res = _render_jinja('base', v)
    #res = _render_jinja('base-test', v)
    if data['report'] == 'animation':
        if data['models']['simulation']['egun_mode'] == '1':
            v['egunStatusFile'] = _EGUN_STATUS_FILE
            res += _render_jinja('egun', v)
        else:
            res += _render_jinja('visualization', v)
        res += _render_jinja('impact-density', v)
    elif data['report'] == 'optimizerAnimation':
        res += _render_jinja('parameters-optimize', v)
    else:
        res += _render_jinja('source-field', v)
        #res += _render_jinja('source-field-test', v)
    return res, v


def _h5_file_list(run_dir, model_name):
    return pkio.walk_tree(
        run_dir.join('diags/xzsolver/hdf5' if model_name == 'currentAnimation' else 'diags/fields/electric'),
        r'\.h5$',
    )


def _is_3D(data):
    return data.models.simulationGrid.simulation_mode == '3d'


def _is_opt_field(field_name):
    return re.search(r'\_opt$', field_name)


def _max_conductor_voltage(data):
    res = data.models.beam.anode_voltage
    for c in data.models.conductors:
        # conductor_type has been added to conductor during _prepare_conductors()
        if c.conductor_type.voltage > res:
            res = c.conductor_type.voltage
    return res


def _meters(v):
    # convert microns to meters
    return float(v) * 1e-6


def _non_opt_fields_to_array(model):
    res = []
    for f in model:
        if not _is_opt_field(f) and f not in _REPORT_STYLE_FIELDS:
            res.append(model[f])
    return res


def _optimizer_percent_complete(run_dir, is_running):
    if not run_dir.exists():
        return {
            'percentComplete': 0,
            'frameCount': 0,
        }
    res, best_row = _read_optimizer_output(run_dir)
    summary_data = None
    frame_count = 0
    data = simulation_db.read_json(run_dir.join(template_common.INPUT_BASE_NAME))
    optimizer = data.models.optimizer
    if res is not None:
        frame_count = len(res)
        if not is_running:
            result_file = run_dir.join(_OPTIMIZER_RESULT_FILE)
            if result_file.exists():
                summary_data = simulation_db.read_json(result_file)
        if not summary_data:
            best_row = best_row.tolist();
            summary_data = {
                'fun': best_row[3],
                'x': best_row[4:],
            }
        summary_data['fields'] = optimizer.fields
    if is_running:
        status_file = run_dir.join(_OPTIMIZER_STATUS_FILE)
        if status_file.exists():
            try:
                if not summary_data:
                    summary_data = {}
                rows = np.loadtxt(str(status_file))
                if len(rows.shape) == 1:
                    rows = np.array([rows])
                summary_data['statusRows'] = rows.tolist()
                summary_data['fields'] = optimizer.fields
                summary_data['frameCount'] = frame_count
                summary_data['initialSteps'] = optimizer.initialSteps
                summary_data['optimizerSteps'] = optimizer.optimizerSteps
            except TypeError:
                pass
            except ValueError:
                pass
    if summary_data:
        return {
            'percentComplete': 0 if is_running else 100,
            'frameCount': frame_count,
            'summary': summary_data,
        }
    if is_running:
        return {
            'percentComplete': 0,
            'frameCount': 0,
        }
    #TODO(pjm): determine optimization error
    return {
        'percentComplete': 0,
        'frameCount': 0,
        'error': 'optimizer produced no data',
        'state': 'error',
    }


def _parse_optimize_field(text):
    # returns (model_name, field_name, container_name, id)
    m, f = text.split('.')
    container, id = None, None
    if re.search(r'#', m):
        name, id = m.split('#')
        container = 'conductors' if name == 'conductorPosition' else 'conductorTypes'
    return m, f, container, id


def _particle_line_has_slope(curr, next, prev, i1, i2):
    return abs(
        _slope(curr[i1], curr[i2], next[i1], next[i2]) - _slope(prev[i1], prev[i2], curr[i1], curr[i2])
    ) >= _CULL_PARTICLE_SLOPE


def _prepare_conductors(data):
    type_by_id = {}
    for ct in data.models.conductorTypes:
        if ct is None:
            continue
        type_by_id[ct.id] = ct
        for f in ('xLength', 'yLength', 'zLength'):
            ct[f] = _meters(ct[f])
        if not _is_3D(data):
            ct.yLength = 1
        ct.permittivity = ct.permittivity if ct.isConductor == '0' else 'None'
        ct.file = template_common.filename_to_path(
            [_stl_file(ct)],
            simulation_db.simulation_lib_dir(data.simulationType)
        )[0] if 'file' in ct else 'None'
    for c in data.models.conductors:
        if c.conductorTypeId not in type_by_id:
            continue
        c.conductor_type = type_by_id[c.conductorTypeId]
        for f in ('xCenter', 'yCenter', 'zCenter'):
            c[f] = _meters(c[f])
        if not _is_3D(data):
            c.yCenter = 0
    return data.models.conductors


def _read_optimizer_output(run_dir):
    # only considers unique points as steps
    opt_file = run_dir.join(_OPTIMIZER_OUTPUT_FILE)
    if not opt_file.exists():
        return None, None
    try:
        values = np.loadtxt(str(opt_file))
        if len(values):
            if len(values.shape) == 1:
                values = np.array([values])
        else:
            return None, None
    except TypeError:
        return None, None
    except ValueError:
        return None, None

    res = []
    best_row = None
    # steps, time, tolerance, result, p1, ... pn
    for v in values:
        res.append(v)
        if best_row is None or v[_OPT_RESULT_INDEX] > best_row[_OPT_RESULT_INDEX]:
            best_row = v
    return np.array(res), best_row


def _render_jinja(template, v):
    return template_common.render_jinja(SIM_TYPE, v, '{}.py'.format(template))


def _replace_optimize_variables(data, v):
    v['optimizeFields'] = []
    v['optimizeConstraints'] = []
    fields = []
    for opt in data.models.optimizer.fields:
        fields.append(opt.field)
    for constraint in data.models.optimizer.constraints:
        for idx in range(len(fields)):
            if constraint[0] == fields[idx]:
                v['optimizeConstraints'].append(idx)
                break
        fields.append(constraint[2])
    for field in fields:
        v['optimizeFields'].append(field)
        value = 'opts[\'{}\']'.format(field)
        m, f, container, id = _parse_optimize_field(field)
        if container:
            model = _find_by_id(data.models[container], id)
            model[f] = value
        else:
            v['{}_{}'.format(m, f)] = value


def _simulation_percent_complete(report, run_dir, is_running):
    if report == 'fieldCalculationAnimation':
        if run_dir.join(_POTENTIAL_FILE).exists():
            return pkcollections.Dict({
                'percentComplete': 100,
                'frameCount': 1,
            })
        return pkcollections.Dict({
            'percentComplete': 0,
            'frameCount': 0,
        })
    files = _h5_file_list(run_dir, 'currentAnimation')
    if (is_running and len(files) < 2) or (not run_dir.exists()):
        return {
            'percentComplete': 0,
            'frameCount': 0,
        }
    if len(files) == 0:
        return {
            'percentComplete': 100,
            'frameCount': 0,
            'error': 'simulation produced no frames',
            'state': 'error',
        }
    file_index = len(files) - 1
    res = {
        'lastUpdateTime': int(os.path.getmtime(str(files[file_index]))),
    }
    # look at 2nd to last file if running, last one may be incomplete
    if is_running:
        file_index -= 1
    data = simulation_db.read_json(run_dir.join(template_common.INPUT_BASE_NAME))
    percent_complete = 0
    if data.models.simulation.egun_mode == '1':
        status_file = run_dir.join(_EGUN_STATUS_FILE)
        if status_file.exists():
            with open(str(status_file), 'r') as f:
                m = re.search('([\d\.]+)\s*/\s*(\d+)', f.read())
            if m:
                percent_complete = float(m.group(1)) / int(m.group(2))
        egun_current_file = run_dir.join(_EGUN_CURRENT_FILE)
        if egun_current_file.exists():
            v = np.load(str(egun_current_file), allow_pickle=True)
            res['egunCurrentFrameCount'] = len(v)
    else:
        percent_complete = (file_index + 1.0) * _PARTICLE_PERIOD / data.models.simulationGrid.num_steps

    if percent_complete < 0:
        percent_complete = 0
    elif percent_complete > 1.0:
        percent_complete = 1.0
    res['percentComplete'] = percent_complete * 100
    res['frameCount'] = file_index + 1
    return res


def _slope(x1, y1, x2, y2):
    if x2 - x1 == 0:
        # treat no slope as flat for comparison
        return 0
    return (y2 - y1) / (x2 - x1)


def _stl_file(conductor_type):
    return template_common.lib_file_name('stl', 'file', conductor_type.file)
