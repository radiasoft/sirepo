# -*- coding: utf-8 -*-
u"""Warp VND/WARP execution template.

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from __future__ import absolute_import, division, print_function
from pykern import pkcollections
from pykern import pkio
from pykern import pkjinja
from pykern.pkdebug import pkdc, pkdp
from rswarp.cathode import sources
from rswarp.utilities.file_utils import readparticles
from scipy import constants
from sirepo import simulation_db
from sirepo.template import template_common
import h5py
import numpy as np
import os.path
import re

SIM_TYPE = 'warpvnd'

WANT_BROWSER_FRAME_CACHE = True

_CULL_PARTICLE_SLOPE = 1e-4

_PARTICLE_PERIOD = 100

_PARTICLE_FILE = 'particles.npy'


def background_percent_complete(report, run_dir, is_running, schema):
    files = _h5_file_list(run_dir, 'currentAnimation')
    if len(files) < 2:
        return {
            'percentComplete': 0,
            'frameCount': 0,
        }
    file_index = len(files) - 1
    last_update_time = int(os.path.getmtime(str(files[file_index])))
    # look at 2nd to last file if running, last one may be incomplete
    if is_running:
        file_index -= 1
    data = simulation_db.read_json(run_dir.join(template_common.INPUT_BASE_NAME))
    percent_complete = (file_index + 1.0) * _PARTICLE_PERIOD / data.models.simulationGrid.num_steps

    if percent_complete < 0:
        percent_complete = 0
    elif percent_complete > 1.0:
        percent_complete = 1.0
    return {
        'lastUpdateTime': last_update_time,
        'percentComplete': percent_complete * 100,
        'frameCount': file_index + 1,
    }


def fixup_old_data(data):
    if 'fieldReport' not in data['models']:
        data['models']['fieldReport'] = {}


def get_animation_name(data):
    return 'animation'


def get_application_data(data):
    if data['method'] == 'compute_simulation_steps':
        run_dir = simulation_db.simulation_dir(SIM_TYPE, data['simulationId']).join('fieldReport')
        if run_dir.exists():
            res = simulation_db.read_result(run_dir)[0]
            if 'tof_expected' in res:
                return {
                    'timeOfFlight': res['tof_expected'],
                    'steps': res['steps_expected'],
                }
        return {}
    raise RuntimeError('unknown application data method: {}'.format(data['method']))


def get_data_file(run_dir, model, frame, **kwargs):
    if model == 'particleAnimation':
        filename = str(run_dir.join(_PARTICLE_FILE))
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
        args = template_common.parse_animation_args(data, {'': ['startTime']})
        data_file = open_data_file(run_dir, data['modelName'], frame_index)
        return _extract_current(model_data, data_file)
    if data['modelName'] == 'fieldAnimation':
        args = template_common.parse_animation_args(data, {'': ['field', 'startTime']})
        data_file = open_data_file(run_dir, data['modelName'], frame_index)
        return _extract_field(args.field, model_data, data_file)
    if data['modelName'] == 'particleAnimation':
        args = template_common.parse_animation_args(data, {'': ['startTime']})
        return _extract_particle(run_dir, model_data)
    raise RuntimeError('{}: unknown simulation frame model'.format(data['modelName']))


def lib_files(data, source_lib):
    """No lib files"""
    return template_common.internal_lib_files([], source_lib)


def models_related_to_report(data):
    """What models are required for this data['report']

    Args:
        data (dict): simulation
    Returns:
        list: Named models, model fields or values (dict, list) that affect report
    """
    return [
        'beam', 'simulationGrid', 'conductors',
    ]


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


def prepare_aux_files(run_dir, data):
    template_common.copy_lib_files(data, None, run_dir)


def python_source_for_model(data, model):
    return _generate_parameters_file(data, is_parallel=True)


def remove_last_frame(run_dir):
    for m in ('currentAnimation', 'fieldAnimation'):
        files = _h5_file_list(run_dir, m)
        if len(files) > 0:
            pkio.unchecked_remove(files[-1])


def write_parameters(data, schema, run_dir, is_parallel):
    """Write the parameters file

    Args:
        data (dict): input
        schema (dict): to validate data
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


def _add_particle_paths(electrons, x_points, y_points):
    # adds paths for the particleAnimation report
    # culls adjacent path points with similar slope
    count = 0
    cull_count = 0
    for i in range(len(electrons[1])):
        xres = []
        yres = []
        num_points = len(electrons[1][i])
        prev_x = None
        prev_y = None
        for j in range(num_points):
            x = electrons[1][i][j]
            y = electrons[0][i][j]
            if j > 0 and j < num_points - 1:
                next_x = electrons[1][i][j+1]
                next_y = electrons[0][i][j+1]
                if (abs(_slope(x, y, next_x, next_y) - _slope(prev_x, prev_y, x, y)) < _CULL_PARTICLE_SLOPE):
                    cull_count += 1
                    continue
            xres.append(x)
            yres.append(y)
            prev_x = x
            prev_y = y
        count += len(xres)
        x_points.append(xres)
        y_points.append(yres)
    pkdc('particles: {} paths, {} points {} points culled', len(x_points), count, cull_count)


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
    beam = data['models']['beam']
    cathode_area = 2. * beam['x_radius'] * 1e-6
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


def _extract_field(field, data, data_file):
    grid = data['models']['simulationGrid']
    plate_spacing = grid['plate_spacing'] * 1e-6
    beam = data['models']['beam']
    radius = beam['x_radius'] * 1e-6
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


def _extract_particle(run_dir, data):
    v = np.load(str(run_dir.join(_PARTICLE_FILE)))
    kept_electrons = v[0]
    lost_electrons = v[1]
    grid = data['models']['simulationGrid']
    plate_spacing = grid['plate_spacing'] * 1e-6
    beam = data['models']['beam']
    radius = beam['x_radius'] * 1e-6
    x_points = []
    y_points = []
    _add_particle_paths(kept_electrons, x_points, y_points)
    lost_x = []
    lost_y = []
    _add_particle_paths(lost_electrons, lost_x, lost_y)
    return {
        'title': 'Particle Trace',
        'x_range': [0, plate_spacing],
        'y_label': 'x [m]',
        'x_label': 'z [m]',
        'points': y_points,
        'x_points': x_points,
        'y_range': [-radius, radius],
        'lost_x': lost_x,
        'lost_y': lost_y,
    }

def _generate_lattice(data):
    conductorTypeMap = {}
    for ct in data.models.conductorTypes:
        conductorTypeMap[ct.id] = ct

    res = 'conductors = ['
    for c in data.models.conductors:
        ct = conductorTypeMap[c.conductorTypeId]
        res += "\n" + '    Box({}, 1., {}, voltage={}, xcent={}, ycent=0.0, zcent={}),'.format(
            float(ct.xLength) * 1e-6, float(ct.zLength) * 1e-6, ct.voltage, float(c.xCenter) * 1e-6, float(c.zCenter) * 1e-6)
    res += '''
]
for c in conductors:
    if c.voltage != 0.0:
      installconductor(c)

scraper = ParticleScraper([source, plate] + conductors, lcollectlpdata=True)
    '''
    return res


def _generate_parameters_file(data, run_dir=None, is_parallel=False, jinja_template=None):
    v = None

    def render(bn):
        b = template_common.resource_dir(SIM_TYPE).join(bn + '.py')
        return pkjinja.render_file(b + '.jinja', v)

    template_common.validate_models(data, simulation_db.get_schema(SIM_TYPE))
    v = template_common.flatten_data(data['models'], {})
    v['outputDir'] = '"{}"'.format(run_dir) if run_dir else None
    v['particlePeriod'] = _PARTICLE_PERIOD
    v['particleFile'] = _PARTICLE_FILE
    v['conductorLatticeAndParticleScraper'] = _generate_lattice(data)
    if not jinja_template:
        jinja_template = 'generate-{}'.format(
            'visualization' if is_parallel else 'source-field')
    return render('base') + render(jinja_template)


def _h5_file_list(run_dir, model_name):
    return pkio.walk_tree(
        run_dir.join('diags/xzsolver/hdf5' if model_name == 'currentAnimation' else 'diags/fields/electric'),
        r'\.h5$',
    )


def _slope(x1, y1, x2, y2):
    if x2 - x1 == 0:
        # treat no slope as flat for comparison
        return 0
    return (y2 - y1) / (x2 - x1)
