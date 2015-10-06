# -*- coding: utf-8 -*-
u"""SRW execution template.

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function

from pykern import pkio
from pykern import pkjinja
from . import template_common
import h5py
import numpy as np
import os
import re

#: How long before killing WARP process
MAX_SECONDS = 60 * 60

_MODE_TEXT = {
    '0': '0',
    '1': '1 (real part)',
    '2': '1 (imaginary part)',
}

def background_percent_complete(data, persistent_files_dir, is_running):
    simulation_id = data['models']['simulation']['simulationId']
    files = _h5_file_list(str(persistent_files_dir.join('diags/hdf5')))
    if len(files) < 2:
        return {
            'percent_complete': 0,
            'frame_count': 0,
        }
    # look at 2nd to last file if running, last one may be incomplete
    name = files[-2 if is_running else -1]
    field = 'E'
    coordinate = 'r'
    mode = 1

    Lplasma_lab = float(data['models']['electronPlasma']['length']) / 1e3
    zmmin = float(data['models']['simulationGrid']['zMin']) / 1e6

    dfile = h5py.File(name, 'r')
    dset = dfile['fields/{}/{}'.format(field, coordinate)]
    F = np.flipud(np.array(dset[mode,:,:]).T)
    Nr, Nz = F.shape[0], F.shape[1]
    dz = dset.attrs['dx']
    dr = dset.attrs['dy']
    zmin = dset.attrs['xmin']
    extent = np.array([zmin-0.5*dz, zmin+0.5*dz+dz*Nz, 0., (Nr+1)*dr])
    edge = zmin + dz * (Nz + 10)
    position = zmmin + edge

    percent_complete = position * 100 / Lplasma_lab

    if percent_complete < 0:
        percent_complete = 0.0
    elif percent_complete > 100:
        percent_complete = 100
    return {
        'percent_complete': percent_complete,
        'frame_count': len(files),
    }


def fixup_old_data(data):
    if 'laserPreviewReport' not in data['models']:
        data['models']['laserPreviewReport'] = {}


def generate_parameters_file(data, schema, persistent_files_dir=None):
    _validate_data(data, schema)
    v = template_common.flatten_data(data['models'], {})
    if persistent_files_dir:
        if not persistent_files_dir.check():
            pkio.mkdir_parent(persistent_files_dir)
        v['outputDir'] = '"{}"'.format(persistent_files_dir)
    else:
        v['outputDir'] = None
    if 'report' in data and data['report'] == 'laserPreviewReport':
        v['enablePlasma'] = 0
    else:
        v['enablePlasma'] = 1
    return pkjinja.render_resource('warp.py', v)


def get_simulation_frame(persistent_files_dir, data):
    frame_index = int(data['frameIndex'])
    files = _h5_file_list(str(persistent_files_dir.join('diags/hdf5')))

    field = data['models']['fieldAnimation']['field']
    coordinate = data['models']['fieldAnimation']['coordinate']
    mode = int(data['models']['fieldAnimation']['mode'])

    filename = files[frame_index]
    iteration = int(re.search(r'data(\d+)', filename).group(1))

    #TODO(pjm): consolidate with pykern_cli/warp.py
    dfile = h5py.File(filename, "r")

    if field == 'rho' :
        dset = dfile['fields/rho']
        coordinate = ''
    else:
        dset = dfile['fields/{}/{}'.format(field, coordinate)]
    F = np.flipud(np.array(dset[mode,:,:]).T)
    Nr, Nz = F.shape[0], F.shape[1]
    dz = dset.attrs['dx']
    dr = dset.attrs['dy']
    zmin = dset.attrs['xmin']
    extent = np.array([zmin-0.5*dz, zmin+0.5*dz+dz*Nz, 0., (Nr+1)*dr])
    return {
        'x_range': [extent[0], extent[1], len(F[0])],
        'y_range': [extent[2], extent[3], len(F)],
        'x_label': 'z [m]',
        'y_label': 'r [m]',
        'title': "{} {} in the mode {} at {:.1f} fs (iteration {})".format(
            field, coordinate, _MODE_TEXT[str(mode)], iteration * 1e15 * float(dfile.attrs['timeStepUnitSI']), iteration),
        'z_matrix': np.flipud(F).tolist(),
        'frameCount': len(files),
    }


def prepare_aux_files(wd):
    pass


def run_all_text():
    return '''
doit = True
while(doit):
    step(10)
    doit = ( w3d.zmmin + top.zgrid < Lplasma )
'''

def _h5_file_list(path_to_dir):
    if not os.path.isdir(path_to_dir):
        return []
    all_files = os.listdir(path_to_dir)

    # Select the hdf5 files
    h5_files = []
    for filename in all_files :
        if filename[-3:] == '.h5' :
            h5_files.append( os.path.join( path_to_dir, filename) )
    # Sort them
    h5_files.sort()
    return h5_files

def _validate_data(data, schema):
    # ensure enums match, convert ints/floats, apply scaling
    enum_info = template_common.parse_enums(schema['enum'])
    for k in data['models']:
        if k in schema['model']:
            template_common.validate_model(data['models'][k], schema['model'][k], enum_info)
