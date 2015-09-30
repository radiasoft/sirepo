# -*- coding: utf-8 -*-
"""Wrapper to run SRW from the command line.

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function

import h5py
import json
import numpy as np

from pykern import pkio

def run(cfg_dir):
    """Run srw in ``cfg_dir``

    The files in ``cfg_dir`` must be configured properly.

    Args:
        cfg_dir (str): directory to run warp in
    """
    with pkio.save_chdir(cfg_dir):
        _run_warp()


def _run_warp():
    with open('in.json') as f:
        data = json.load(f)

    exec(pkio.read_text('warp_parameters.py'), locals(), locals())
    step(400)

    dfile = h5py.File('diags/hdf5/data00000400.h5', "r")
    dset = dfile['fields/E/r']
    mCompAzimuthal = 1
    F = np.flipud(np.array(dset[mCompAzimuthal,:,:]).T)
    Nr, Nz = F.shape[0], F.shape[1]
    dz = dset.attrs['dx']
    dr = dset.attrs['dy']
    zmin = dset.attrs['xmin']
    extent = np.array([zmin-0.5*dz, zmin+0.5*dz+dz*Nz, 0., (Nr+1)*dr])
    data = {
        'x_range': [extent[0], extent[1], len(F[0])],
        'y_range': [extent[2], extent[3], len(F)],
        'x_label': 'z (µm)',
        'y_label': 'r (µm)',
        'title': 'E r in mode 1 (real) at 44.2 fs (iteration 400)',
        'z_matrix': np.flipud(F).tolist(),
    }
    with open ('out.json', 'w') as f:
        json.dump(data, f)
