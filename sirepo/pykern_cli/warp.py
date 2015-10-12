# -*- coding: utf-8 -*-
"""Wrapper to run SRW from the command line.

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function

import h5py
import json
import numpy as np
import time

from pykern import pkio

_MODE_TEXT = {
    '0': '0',
    '1': '1 (real part)',
    '2': '1 (imaginary part)',
}


def run(cfg_dir):
    """Run srw in ``cfg_dir``

    The files in ``cfg_dir`` must be configured properly.

    Args:
        cfg_dir (str): directory to run warp in
    """
    with pkio.save_chdir(cfg_dir):
        _run_warp()


def run_background(cfg_dir, persistent_file_dir):
    with pkio.save_chdir(cfg_dir):
        exec(pkio.read_text('warp_parameters.py'), locals(), locals())
        doit = True
        while(doit):
            step(10)
            doit = ( w3d.zmmin + top.zgrid < Lplasma )

def _run_warp(persistent_file_dir=None):
    with open('in.json') as f:
        data = json.load(f)

    field = 'E'
    coordinate = 'r'
    mode = 1

    exec(pkio.read_text('warp_parameters.py'), locals(), locals())
    iteration = 0

    doit = True
    while(doit):
        step(50)
        iteration += 50
        doit = ( w3d.zmmin + top.zgrid < 0 )

    out_dir = (persistent_file_dir + '/') if persistent_file_dir else ''
    dfile = h5py.File(out_dir + 'diags/hdf5/data' + str(iteration).zfill(8) + '.h5', "r")
    dset = dfile['fields/{}/{}'.format(field, coordinate)]
    F = np.flipud(np.array(dset[mode,:,:]).T)
    Nr, Nz = F.shape[0], F.shape[1]
    dz = dset.attrs['dx']
    dr = dset.attrs['dy']
    zmin = dset.attrs['xmin']
    extent = np.array([zmin-0.5*dz, zmin+0.5*dz+dz*Nz, 0., (Nr+1)*dr])
    data = {
        'x_range': [extent[0], extent[1], len(F[0])],
        'y_range': [extent[2], extent[3], len(F)],
        'x_label': 'z [m]',
        'y_label': '{} [m]'.format(coordinate),
        'title': "{} {} in the mode {} at {:.1f} fs (iteration {})".format(
            field, coordinate, _MODE_TEXT[str(mode)], iteration * 1e15 * float(dfile.attrs['timeStepUnitSI']), iteration),
        'z_matrix': np.flipud(F).tolist(),
    }
    with open ('out.json', 'w') as f:
        json.dump(data, f)
