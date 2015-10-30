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
from sirepo.template.warp import extract_field_report

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


def run_background(cfg_dir):
    with pkio.save_chdir(cfg_dir):
        exec(pkio.read_text('warp_parameters.py'), locals(), locals())
        doit = True
        while(doit):
            step(10)
            doit = ( w3d.zmmin + top.zgrid < Lplasma )


def _run_warp():
    with open('in.json') as f:
        data = json.load(f)

    field = data['models']['laserPreviewReport']['field']
    coordinate = data['models']['laserPreviewReport']['coordinate']
    mode = int(data['models']['laserPreviewReport']['mode'])
    exec(pkio.read_text('warp_parameters.py'), locals(), locals())
    iteration = 0

    doit = True
    while(doit):
        step(50)
        iteration += 50
        doit = ( w3d.zmmin + top.zgrid < 0 )

    dfile = h5py.File('diags/hdf5/data' + str(iteration).zfill(8) + '.h5', "r")
    res = extract_field_report(field, coordinate, mode, dfile, iteration)

    with open ('out.json', 'w') as f:
        json.dump(res, f)
