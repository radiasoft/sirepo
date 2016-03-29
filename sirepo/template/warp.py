#TODO(robnagler) fix up old data(?) probably just remove
#TODO(robnagler) fix up other simulations to use template_common(?)

# -*- coding: utf-8 -*-
u"""SRW execution template.

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkcollections
from pykern import pkio
from pykern import pkjinja
from pykern.pkdebug import pkdc, pkdp
from sirepo import simulation_db
from sirepo.template import template_common
import h5py
import numpy
import os
import py.path
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
    params = simulation_db.read_json(run_dir.join(template_common.PARAMETERS_BASE_NAME))
    total_frames = int(params['numSteps'] / params['incSteps'])
    percent_complete = (file_index + 1) / total_frames * 100
    return {
        'percent_complete': percent_complete,
        'frame_count': file_index + 1,
        'total_frames': total_frames,
    }


def copy_animation_file(source_path, target_path):
    pass


def extract_field_report(field, coordinate, mode, data_file):
    fields = data_file.h5['data/{}/fields'.format(data_file.iteration)]
    from opmd_viewer import OpenPMDTimeSeries
    o = OpenPMDTimeSeries(py.path.local(data_file.filename).dirname)
    F, info = o.get_field(
        plot=False,
        vmin=None,
        m=mode,
        coord=coordinate,
        iteration=data_file.iteration,
        slicing=0.0,
        field=field,
        theta=0.0,
        vmax=None,
        output=True,
        slicing_dir='y',

    )
    extent = info.imshow_extent
    return {
        'x_range': [extent[0], extent[1], len(F[0])],
        'y_range': [extent[2], extent[3], len(F)],
        'x_label': 'x [m]',
        'y_label': 'y [m]',
        'title': "{} {} in the mode {} at {}".format(
            field, coordinate, _MODE_TEXT[str(mode)], _iteration_title(data_file)),
        'z_matrix': numpy.flipud(F).tolist(),
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
    v['numSteps'] = 1000 if run_async else 640
    v['incSteps'] = 20
    if run_dir:
        simulation_db.write_json(run_dir.join(template_common.PARAMETERS_BASE_NAME), v)
    return pkjinja.render_resource('warp.py', v)


def get_animation_name(data):
    return 'animation'


def get_simulation_frame(run_dir, data):
    frame_index = int(data['frameIndex'])
    data_file = open_data_file(run_dir, frame_index)
    args = data['animationArgs'].split('_')
    if data['modelName'] == 'fieldAnimation':
        return _field_animation(args, data_file)
    if data['modelName'] == 'particleAnimation':
        return _particle_animation(args, data_file)
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


def open_data_file(run_dir, file_index=None, files=None):
    """Opens data file_index'th in run_dir

    Args:
        run_dir (py.path): has subdir ``hdf5``
        file_index (int): which file to open (default: last one)
        files (list): list of files (default: load list)

    Returns:
        OrderedMapping: various parameters
    """
    if not files:
        files = _h5_file_list(run_dir)
    res = pkcollections.OrderedMapping()
    res.num_frames = len(files)
    res.frame_index = res.num_frames - 1 if file_index is None else file_index
    res.filename = str(files[res.frame_index])
    res.iteration = int(re.search(r'data(\d+)', res.filename).group(1))
    res.h5 = h5py.File(res.filename, 'r')
    ds = res.h5['data'][str(res.iteration)]
    res.data_set = ds
    res.time = ds.attrs['time'] * ds.attrs['timeUnitSI']
    return res


def prepare_aux_files(run_dir, data):
    pass


def remove_last_frame(run_dir):
    files = _h5_file_list(run_dir)
    if len(files) > 0:
        pkio.unchecked_remove(files[-1])


def run_all_text():
    return ''


def write_parameters(data, schema, run_dir, run_async):
    """Write the parameters file

    Args:
        data (dict): input
        schema (dict): to validate data
        run_dir (py.path): where to write
        run_async (bool): run in background?
    """
    pkio.write_text(
        run_dir.join(template_common.PARAMETERS_PYTHON_FILE),
        generate_parameters_file(
            data,
            schema,
            run_dir,
            run_async,
        ),
    )


def static_lib_files():
    """Library shared between simulations of this type

    Returns:
        list: py.path.local objects
    """
    return []


def _field_animation(args, data_file):
    field = args[0]
    coordinate = args[1]
    mode = int(args[2])
    res = extract_field_report(field, coordinate, mode, data_file)
    res['frameCount'] = data_file.num_frames
    return res


def _h5_file_list(run_dir):
    return pkio.walk_tree(
        run_dir.join('hdf5'),
        r'\.h5$',
    )


def _iteration_title(data_file):
    fs = data_file.time / 1e-15
    return '{:.1f} fs (iteration {})'.format(fs, data_file.iteration)


def _particle_animation(args, data_file):
    xarg = args[0]
    yarg = args[1]
    histogramBins = args[2]
    ds = data_file.data_set
    x = ds['particles/electrons/{}'.format(_PARTICLE_ARG_PATH[xarg])][:]
    y = ds['particles/electrons/{}'.format(_PARTICLE_ARG_PATH[yarg])][:]
    hist, edges = numpy.histogramdd([x, y], int(histogramBins))
    xunits = ' [m]' if len(xarg) == 1 else ''
    yunits = ' [m]' if len(yarg) == 1 else ''
    return {
        'x_range': [float(edges[0][0]), float(edges[0][-1]), len(hist)],
        'y_range': [float(edges[1][0]), float(edges[1][-1]), len(hist[0])],
        'x_label': '{}{}'.format(xarg, xunits),
        'y_label': '{}{}'.format(yarg, yunits),
        'title': 't = {}'.format(_iteration_title(data_file)),
        'z_matrix': hist.T.tolist(),
        'frameCount': data_file.num_frames,
    }


def _validate_data(data, schema):
    # ensure enums match, convert ints/floats, apply scaling
    enum_info = template_common.parse_enums(schema['enum'])
    for k in data['models']:
        if k in schema['model']:
            template_common.validate_model(data['models'][k], schema['model'][k], enum_info)
