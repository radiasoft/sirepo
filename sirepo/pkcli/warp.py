# -*- coding: utf-8 -*-
"""Wrapper to run SRW from the command line.

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkio
from pykern.pkdebug import pkdp
import h5py
import json
import numpy as np
import py.path
import sirepo.simulation_db as sdb
import sirepo.template.warp as tw
import time

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


def _run_warp():
    with open('in.json') as f:
        data = json.load(f)
    field = data['models']['laserPreviewReport']['field']
    coordinate = data['models']['laserPreviewReport']['coordinate']
    mode = int(data['models']['laserPreviewReport']['mode'])
    exec(pkio.read_text('warp_parameters.py'), locals(), locals())
    dfile, iteration, _ = tw.open_data_file(py.path.local())
    res = tw.extract_field_report(field, coordinate, mode, dfile, iteration)
    sdb.write_json('out', res)
