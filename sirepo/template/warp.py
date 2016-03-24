# -*- coding: utf-8 -*-
u"""SRW execution template.

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function

from pykern.pkdebug import pkdc, pkdp
from pykern import pkio
from pykern import pkjinja
from sirepo.template import template_common
import h5py
import numpy as np
import os
import re

WANT_BROWSER_FRAME_CACHE = True

_MODE_TEXT = {
    '0': '0',
    '1': '1 (real part)',
    '2': '1 (imaginary part)',
}

_PARTICLE_ARG_PATH = {
    'x' : 'position/x',
    'y' : 'position/y',
    'z' : 'position/z',
    'ux' : 'momentum/x',
    'uy' : 'momentum/y',
    'uz' : 'momentum/z',
}


def background_percent_complete(data, run_dir, is_running):
    simulation_id = data['models']['simulation']['simulationId']
    files = _h5_file_list(run_dir)
    if len(files) < 2:
        return {
            'percent_complete': 0,
            'frame_count': 0,
            'total_frames': 0,
        }
    file_index = len(files) - 1
    # look at 2nd to last file if running, last one may be incomplete
    if is_running:
        file_index -= 1
    dfile, iteration, _ = open_data_file(run_dir, file_index, files)
    percent_complete = 0
    return {
        'percent_complete': percent_complete * 100,
        'frame_count': file_index + 1,
        'total_frames': 1000,
    }


def copy_animation_file(source_path, target_path):
    pass


def extract_field_report(field, coordinate, mode, dfile, iteration):
    pkdp([field, coordinate, mode, iteration])
    fields = dfile['data/{}/fields'.format(iteration)]
    if field == 'rho' :
        dset = fields['rho']
        coordinate = ''
    else:
        dset = fields['{}/{}'.format(field, coordinate)]
    F = np.flipud(np.array(dset[mode,:,:]).T)
    Nr, Nz = F.shape[0], F.shape[1]
    dr = fields[field].attrs['gridSpacing'][0]
    dz = fields[field].attrs['gridSpacing'][1]
    zmin = fields[field].attrs['gridGlobalOffset'][1]
    extent = np.array([zmin-0.5*dz, zmin+0.5*dz+dz*Nz, 0., (Nr+1)*dr])
    return {
        'x_range': [extent[0], extent[1], len(F[0])],
        'y_range': [extent[2], extent[3], len(F)],
        'x_label': 'z [m]',
        'y_label': 'r [m]',
        'title': "{} {} in the mode {} at {}".format(
            field, coordinate, _MODE_TEXT[str(mode)], _iteration_title(dfile, iteration)),
        'z_matrix': np.flipud(F).tolist(),
    }


def fixup_old_data(data):
    if 'laserPreviewReport' not in data['models']:
        data['models']['laserPreviewReport'] = {}
    if 'particleAnimation' not in data['models']:
        data['models']['particleAnimation'] = {
            'x': 'z',
            'y': 'x',
            'histogramBins': 100,
        }
    if 'simulationStatus' not in data['models']:
        data['models']['simulationStatus'] = {
            'startTime': 0,
            'state': 'initial',
        }
    if 'startTime' not in data['models']['simulationStatus']:
        data['models']['simulationStatus']['startTime'] = 0
    if 'histogramBins' not in data['models']['particleAnimation']:
        data['models']['particleAnimation']['histogramBins'] = 100
    if 'framesPerSecond' not in data['models']['fieldAnimation']:
        data['models']['fieldAnimation']['framesPerSecond'] = 20
        data['models']['particleAnimation']['framesPerSecond'] = 20
    if 'rScale' not in data['models']['simulationGrid']:
        grid = data['models']['simulationGrid']
        grid['rScale'] = 4
        grid['rLength'] = '20.324980154380'
        grid['rMin'] = 0
        grid['rMax'] = '20.324980154380'
        grid['rCellsPerSpotSize'] = 8
        grid['rCount'] = 32
        grid['zScale'] = 2
        grid['zLength'] = '20.324980154631'
        grid['zMin'] = '-20.324980154631'
        grid['zMax'] = '1.60'
        grid['zCellsPerWavelength'] = 8
        grid['zCount'] = 214
        del grid['xMin']
        del grid['xMax']
        del grid['xCount']
        del grid['zLambda']
    if 'rParticlesPerCell' not in data['models']['simulationGrid']:
        data['models']['simulationGrid']['rParticlesPerCell'] = 1
        data['models']['simulationGrid']['zParticlesPerCell'] = 2
    if 'field' not in data['models']['laserPreviewReport']:
        laserPreview = data['models']['laserPreviewReport']
        laserPreview['field'] = 'E'
        laserPreview['coordinate'] = 'r'
        laserPreview['mode'] = '1'


def generate_parameters_file(data, schema, run_dir=None, run_async=False):
    _validate_data(data, schema)
    v = template_common.flatten_data(data['models'], {})
    v['outputDir'] = '"{}"'.format(run_dir) if run_dir else None
    v['enablePlasma'] = 1
    v['isAnimationView'] = run_async
    return pkjinja.render_resource('warp.py', v)


def get_simulation_frame(run_dir, data):
    frame_index = int(data['frameIndex'])
    dfile, iteration, num_frames = open_data_file(run_dir, frame_index)
    args = data['animationArgs'].split('_')
    if data['modelName'] == 'fieldAnimation':
        return _field_animation(args, dfile, iteration, num_frames)
    if data['modelName'] == 'particleAnimation':
        return _particle_animation(args, dfile, iteration, num_frames)
    raise RuntimeError('{}: unknown simulation frame model'.format(data['modelName']))


def get_data_file(run_dir, frame_index):
    files = _h5_file_list(run_dir)
    #TODO(pjm): last client file may have been deleted on a canceled animation,
    # give the last available file instead.
    if len(files) < frame_index + 1:
        frame_index = -1
    filename = str(files[int(frame_index)])
    with open(filename) as f:
        return os.path.basename(filename), f.read(), 'application/octet-stream'


def new_simulation(data, new_simulation_data):
    pass


def open_data_file(run_dir, frame_index=None, files=None):
    pkdp(run_dir)
    if not files:
        files = _h5_file_list(run_dir)
    num_frames = len(files)
    pkdp([frame_index, num_frames])
    filename = str(files[(num_frames - 1) if frame_index is None else frame_index])
    iteration = int(re.search(r'data(\d+)', filename).group(1))
    return h5py.File(filename, 'r'), iteration, num_frames


def prepare_aux_files(run_dir, data):
    pass


def remove_last_frame(run_dir):
    files = _h5_file_list(run_dir)
    if len(files) > 0:
        pkio.unchecked_remove(files[-1])


def run_all_text():
    return ''


def static_lib_files():
    """Library shared between simulations of this type

    Returns:
        list: py.path.local objects
    """
    return []


def _field_animation(args, dfile, iteration, frame_count):
    field = args[0]
    coordinate = args[1]
    mode = int(args[2])
    res = extract_field_report(field, coordinate, mode, dfile, iteration)
    res['frameCount'] = frame_count
    return res


def _h5_file_list(run_dir):
    return pkio.walk_tree(
        run_dir.join('hdf5'),
        r'\.h5$',
    )


def _iteration_title(dfile, iteration):
    return '{:.1f} fs (iteration {})'.format(
        iteration * float(dfile['data'][str(iteration)].attrs['timeUnitSI']), iteration)


def _particle_animation(args, dfile, iteration, frame_count):
    xarg = args[0]
    yarg = args[1]
    histogramBins = args[2]
    dset = dfile['data/{}'.format(iteration)]
    x = dset['particles/electrons/{}'.format(_PARTICLE_ARG_PATH[xarg])][:]
    y = dset['particles/electrons/{}'.format(_PARTICLE_ARG_PATH[yarg])][:]
    hist, edges = np.histogramdd([x, y], int(histogramBins))
    xunits = ' [m]' if len(xarg) == 1 else ''
    yunits = ' [m]' if len(yarg) == 1 else ''
    return {
        'x_range': [float(edges[0][0]), float(edges[0][-1]), len(hist)],
        'y_range': [float(edges[1][0]), float(edges[1][-1]), len(hist[0])],
        'x_label': '{}{}'.format(xarg, xunits),
        'y_label': '{}{}'.format(yarg, yunits),
        'title': 't = {}'.format(_iteration_title(dfile, iteration)),
        'z_matrix': hist.T.tolist(),
        'frameCount': frame_count,
    }


def _validate_data(data, schema):
    # ensure enums match, convert ints/floats, apply scaling
    enum_info = template_common.parse_enums(schema['enum'])
    for k in data['models']:
        if k in schema['model']:
            template_common.validate_model(data['models'][k], schema['model'][k], enum_info)
