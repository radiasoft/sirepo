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
from sirepo import simulation_db
import sirepo.template.warp as template
from sirepo.template import template_common
import time

def run(cfg_dir):
    """Run srw in ``cfg_dir``

    The files in ``cfg_dir`` must be configured properly.

    Args:
        cfg_dir (str): directory to run warp in
    """
    with pkio.save_chdir(cfg_dir):
        _run_warp()
        data = simulation_db.read_json(template_common.INPUT_BASE_NAME)
        field = data['models']['laserPreviewReport']['field']
        coordinate = data['models']['laserPreviewReport']['coordinate']
        mode = data['models']['laserPreviewReport']['mode']
        if mode != 'all':
            mode = int(mode)
        data_file = template.open_data_file(py.path.local())
        res = template.extract_field_report(field, coordinate, mode, data_file)
        simulation_db.write_json(template_common.OUTPUT_BASE_NAME, res)


def run_background(cfg_dir):
    """Run srw in ``cfg_dir``

    The files in ``cfg_dir`` must be configured properly.

    Args:
        cfg_dir (str): directory to run warp in
    """
    with pkio.save_chdir(cfg_dir):
        _run_warp()


def _run_warp():
    """Run warp program with isolated locals()
    """
    exec(pkio.read_text(template_common.PARAMETERS_PYTHON_FILE), locals(), locals())
