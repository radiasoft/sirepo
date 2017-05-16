# -*- coding: utf-8 -*-
"""Wrapper to run FETE/WARP from the command line.

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkio
from pykern.pkdebug import pkdp, pkdc
from sirepo import mpi
from sirepo import simulation_db
from sirepo.template import template_common
import sirepo.template.fete as template


def run(cfg_dir):
    raise RuntimeError('not implemented')


def run_background(cfg_dir):
    """Run fete in ``cfg_dir`` with mpi

    Args:
        cfg_dir (str): directory to run fete in
    """
    with pkio.save_chdir(cfg_dir):
        mpi.run_script(_script())
        simulation_db.write_result({})


def _script():
    return pkio.read_text(template_common.PARAMETERS_PYTHON_FILE)
