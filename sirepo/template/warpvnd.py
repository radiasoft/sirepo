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
import random

COMPARISON_STEP_SIZE = 100
SIM_TYPE = 'warpvnd'
WANT_BROWSER_FRAME_CACHE = True

_COMPARISON_FILE = 'diags/fields/electric/data00{}.h5'.format(COMPARISON_STEP_SIZE)
_CULL_PARTICLE_SLOPE = 1e-4
_DENSITY_FILE = 'density.npy'
_EGUN_CURRENT_FILE = 'egun-current.npy'
_EGUN_STATUS_FILE = 'egun-status.txt'
_PARTICLE_PERIOD = 100
_PARTICLE_FILE = 'particles.npy'
_REPORT_STYLE_FIELDS = ['colorMap', 'notes']
_SCHEMA = simulation_db.get_schema(SIM_TYPE)

def background_percent_complete(report, run_dir, is_running):
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
            v = np.load(str(egun_current_file))
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


def fixup_old_data(data):
    for m in [
            'egunCurrentAnimation',
            'fieldReport',
            'impactDensityAnimation',
            'particle3d',
            'particleAnimation',
            'simulation',
            'simulationGrid',
    ]:
        if m not in data['models']:
            data['models'][m] = {}
        template_common.update_model_defaults(data['models'][m], m, _SCHEMA)
    if data['models']['particle3d']['joinEvery'] < 5:
        data['models']['particle3d']['joinEvery'] = 5
    for c in data['models']['conductorTypes']:
        if 'isConductor' not in c:
            c['isConductor'] = '1' if c['voltage'] > 0 else '0'
        template_common.update_model_defaults(c, 'box', _SCHEMA)
    for c in data['models']['conductors']:
        template_common.update_model_defaults(c, 'conductorPosition', _SCHEMA)
    if 'fieldComparisonReport' not in data['models']:
        grid = data['models']['simulationGrid']
        data['models']['fieldComparisonReport'] = {
            'dimension': 'x',
            'xCell1': int(grid['num_x'] / 3.),
            'xCell2': int(grid['num_x'] / 2.),
            'xCell3': int(grid['num_x'] * 2. / 3),
            'zCell1': int(grid['num_z'] / 2.),
            'zCell2': int(grid['num_z'] * 2. / 3),
            'zCell3': int(grid['num_z'] * 4. / 5),
        }


def generate_field_comparison_report(data, run_dir):
    params = data['models']['fieldComparisonReport']
    dimension = params['dimension']
    with h5py.File(str(py.path.local(run_dir).join(_COMPARISON_FILE))) as f:
        values = f['data/{}/meshes/E/{}'.format(COMPARISON_STEP_SIZE, dimension)]
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


def get_animation_name(data):
    return 'animation'


def get_application_data(data):
    if data['method'] == 'compute_simulation_steps':
        run_dir = simulation_db.simulation_dir(SIM_TYPE, data['simulationId']).join('fieldReport')
        if run_dir.exists():
            res = simulation_db.read_result(run_dir)[0]
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
    raise RuntimeError('{}: unknown simulation frame model'.format(data['modelName']))


def lib_files(data, source_lib):
    """No lib files"""
    return []


def models_related_to_report(data):
    """What models are required for this data['report']

    Args:
        data (dict): simulation
    Returns:
        list: Named models, model fields or values (dict, list) that affect report
    """
    if data['report'] == 'animation':
        return []
    res = ['beam', 'simulationGrid', 'conductors', 'conductorTypes']
    if data['report'] != 'fieldComparisonReport':
        res.append(template_common.report_fields(data, data['report'], _REPORT_STYLE_FIELDS))
    return res


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


def prepare_output_file(report_info, data):
    if data['report'] == 'fieldComparisonReport':
        run_dir = report_info.run_dir
        fn = simulation_db.json_filename(template_common.OUTPUT_BASE_NAME, run_dir)
        if fn.exists():
            fn.remove()
            simulation_db.write_result(generate_field_comparison_report(data, run_dir), run_dir=run_dir)


def python_source_for_model(data, model):
    return _generate_parameters_file(data, is_parallel=True)


def remove_last_frame(run_dir):
    for m in ('currentAnimation', 'fieldAnimation'):
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
    pkio.write_text(
        run_dir.join(template_common.PARAMETERS_PYTHON_FILE),
        _generate_parameters_file(
            data,
            run_dir,
            is_parallel,
        ),
    )


def _add_particle_paths(electrons, x_points, y_points, z_points, half_height, limit):
    # adds paths for the particleAnimation report
    # culls adjacent path points with similar slope
    # TODO: include z value when available
    count = 0
    cull_count = 0
    random.seed()
    for i in range(min(len(electrons[1]), limit)):
        xres = []
        yres = []
        zres = []
        num_points = len(electrons[1][i])
        prev_x = None
        prev_y = None
        # prev_z = None
        z = half_height * (2.0 * random.random() - 1.0)
        for j in range(num_points):
            x = electrons[1][i][j]
            y = electrons[0][i][j]
            # z = electrons[2][i][j]
            if j > 0 and j < num_points - 1:
                next_x = electrons[1][i][j+1]
                next_y = electrons[0][i][j+1]
                if (abs(_slope(x, y, next_x, next_y) - _slope(prev_x, prev_y, x, y)) < _CULL_PARTICLE_SLOPE):
                    cull_count += 1
                    continue
            xres.append(x)
            yres.append(y)
            zres.append(z)
            prev_x = x
            prev_y = y
            # prev_z = z
        count += len(xres)
        x_points.append(xres)
        y_points.append(yres)
        z_points.append(zres)
    pkdc('particles: {} paths, {} points {} points culled', len(x_points), count, cull_count)


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
            #TODO(pjm): refactor with template_common.compute_plot_color_and_range()
            'color': color[i - 1],
            'label': u'{} Location {}'.format('Z' if dimension == 'x' else 'X', pos),
        })
        if y_range:
            y_range[0] = min(y_range[0], min(points))
            y_range[1] = max(y_range[1], max(points))
        else:
            y_range = [min(points), max(points)]
    return plots, y_range


def _extract_current(data, data_file):
    grid = data['models']['simulationGrid']
    plate_spacing = grid['plate_spacing'] * 1e-6
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
    plate_spacing = grid['plate_spacing'] * 1e-6
    zmesh = np.linspace(0, plate_spacing, grid['num_z'] + 1) #holds the z-axis grid points in an array
    beam = data['models']['beam']
    cathode_area = grid['channel_width'] * 1e-6
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
    v = np.load(str(data_file))
    if frame_index >= len(v):
        frame_index = -1;
    # the first element in the array is the time, the rest are the current measurements
    return _extract_current_results(data, v[frame_index][1:], v[frame_index][0])


def _extract_field(field, data, data_file):
    grid = data['models']['simulationGrid']
    plate_spacing = grid['plate_spacing'] * 1e-6
    beam = data['models']['beam']
    radius = grid['channel_width'] / 2. * 1e-6
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
        'aspect_ratio': 6.0 / 14,
        'z_matrix': values.tolist(),
    }


def _extract_impact_density(run_dir, data):
    plot_info = np.load(str(run_dir.join(_DENSITY_FILE))).tolist()
    if 'error' in plot_info:
        return plot_info
    grid = data['models']['simulationGrid']
    plate_spacing = grid['plate_spacing'] * 1e-6
    beam = data['models']['beam']
    radius = grid['channel_width'] / 2. * 1e-6

    dx = plot_info['dx']
    dz = plot_info['dz']
    gated_ids = plot_info['gated_ids']
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
        'y_label': 'x [m]',
        'x_label': 'z [m]',
        'density_lines': lines,
        'v_min': plot_info['min'],
        'v_max': plot_info['max'],
    }


def _extract_particle(run_dir, data, limit):
    v = np.load(str(run_dir.join(_PARTICLE_FILE)))
    kept_electrons = v[0]
    lost_electrons = v[1]
    grid = data['models']['simulationGrid']
    plate_spacing = grid['plate_spacing'] * 1e-6
    beam = data['models']['beam']
    radius = grid['channel_width'] / 2. * 1e-6
    half_height = grid['channel_height'] if 'channel_height' in grid else 5.
    half_height = half_height / 2. * 1e-6
    x_points = []
    y_points = []
    z_points = []
    # TODO(mvk): get zpoints from data.  For now we generate random data to fit the geometry
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


def _generate_impact_density():
    return '''
from rswarp.diagnostics import ImpactDensity
try:
    plot_density = ImpactDensity.PlotDensity(None, None, scraper, top, w3d)
    plot_density.gate_scraped_particles()
    plot_density.map_density()
    for gid in plot_density.gated_ids:
        for side in plot_density.gated_ids[gid]:
            del plot_density.gated_ids[gid][side]['interpolation']
    density_results = {
        'gated_ids': plot_density.gated_ids,
        'dx': plot_density.dx,
        'dz': plot_density.dz,
        'min': plot_density.cmap_normalization.vmin,
        'max': plot_density.cmap_normalization.vmax,
    }
except AssertionError as e:
    density_results = {
        'error': e.message,
    }
    ''' + '''
np.save('{}', density_results)
    '''.format(_DENSITY_FILE)


def _generate_lattice(data):
    conductorTypeMap = {}
    for ct in data.models.conductorTypes:
        conductorTypeMap[ct.id] = ct

    res = 'conductors = ['
    for c in data.models.conductors:
        ct = conductorTypeMap[c.conductorTypeId]
        permittivity = ''
        if ct.isConductor == '0':
            permittivity = ', permittivity={}'.format(float(ct.permittivity))
        res += "\n" + '    Box({}, 1., {}, voltage={}, xcent={}, ycent=0.0, zcent={}{}),'.format(
            float(ct.xLength) * 1e-6, float(ct.zLength) * 1e-6, ct.voltage, float(c.xCenter) * 1e-6, float(c.zCenter) * 1e-6, permittivity)
    res += '''
]
for c in conductors:
    if c.voltage != 0.0:
      installconductor(c)

scraper = ParticleScraper([source, plate] + conductors, lcollectlpdata=True)
    '''
    return res


def _generate_parameters_file(data, run_dir=None, is_parallel=False):
    v = None
    template_common.validate_models(data, _SCHEMA)
    v = template_common.flatten_data(data['models'], {})
    v['outputDir'] = '"{}"'.format(run_dir) if run_dir else None
    v['particlePeriod'] = _PARTICLE_PERIOD
    v['particleFile'] = _PARTICLE_FILE
    v['impactDensityCalculation'] = _generate_impact_density()
    v['egunCurrentFile'] = _EGUN_CURRENT_FILE
    v['conductorLatticeAndParticleScraper'] = _generate_lattice(data)
    v['maxConductorVoltage'] = _max_conductor_voltage(data)
    template_name = ''
    if 'report' not in data:
        template_name = 'visualization'
    elif data['report'] == 'animation':
        if data['models']['simulation']['egun_mode'] == '1':
            v['egunStatusFile'] = _EGUN_STATUS_FILE
            template_name = 'egun'
        else:
            template_name = 'visualization'
    else:
        template_name = 'source-field'
    return template_common.render_jinja(SIM_TYPE, v, 'base.py') \
        + template_common.render_jinja(SIM_TYPE, v, '{}.py'.format(template_name))


def _h5_file_list(run_dir, model_name):
    return pkio.walk_tree(
        run_dir.join('diags/xzsolver/hdf5' if model_name == 'currentAnimation' else 'diags/fields/electric'),
        r'\.h5$',
    )


def _max_conductor_voltage(data):
    type_by_id = {}
    for conductor_type in data.models.conductorTypes:
        type_by_id[conductor_type.id] = conductor_type
    max_voltage = data.models.beam.anode_voltage
    for conductor in data.models.conductors:
        conductor_type = type_by_id[conductor.conductorTypeId]
        if conductor_type.voltage > max_voltage:
            max_voltage = conductor_type.voltage
    return max_voltage


def _slope(x1, y1, x2, y2):
    if x2 - x1 == 0:
        # treat no slope as flat for comparison
        return 0
    return (y2 - y1) / (x2 - x1)
