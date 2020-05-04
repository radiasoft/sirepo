# -*- coding: utf-8 -*-
"""Wrapper to run Radia from the command line.

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkio
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdc
from sirepo import mpi
from sirepo import simulation_db
from sirepo.template import template_common
import py.path
import sirepo.template.radia as template


def run(cfg_dir):
    template_common.exec_parameters()
    data = simulation_db.read_json(template_common.INPUT_BASE_NAME)
    template.extract_report_data(py.path.local(cfg_dir), data)


def run_background(cfg_dir):
    """Run warpvnd in ``cfg_dir`` with mpi

    Args:
        cfg_dir (str): directory to run warpvnd in
    """
    # limit to 1 until we do parallel properly
    res = PKDict()
    mpi.cfg.cores = 1
    simulation_db.write_json(py.path.local(cfg_dir).join(template.MPI_SUMMARY_FILE), {
        'mpiCores': mpi.cfg.cores,
    })
    try:
        template_common.exec_parameters_with_mpi()
    except Exception as e:
        res.error = str(e)
    simulation_db.write_result(res)


def _script():
    return pkio.read_text(template_common.PARAMETERS_PYTHON_FILE)
