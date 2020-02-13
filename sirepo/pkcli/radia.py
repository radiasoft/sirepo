# -*- coding: utf-8 -*-
"""Wrapper to run Radia from the command line.

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkio
from pykern.pkdebug import pkdp, pkdc
from sirepo import mpi
from sirepo import simulation_db
from sirepo.template import template_common
import py.path
import sirepo.template.radia as template


def run(cfg_dir):
    with pkio.save_chdir(cfg_dir):
        _run_simulation()
        data = simulation_db.read_json(template_common.INPUT_BASE_NAME)
        template.extract_report_data(py.path.local(cfg_dir), data)


def run_background(cfg_dir):
    """Run warpvnd in ``cfg_dir`` with mpi

    Args:
        cfg_dir (str): directory to run warpvnd in
    """
    with pkio.save_chdir(cfg_dir):
        simulation_db.write_json(py.path.local(cfg_dir).join(template.MPI_SUMMARY_FILE), {
            'mpiCores': mpi.cfg.cores,
        })
        mpi.run_script(_run_simulation())
        simulation_db.write_result({})


def _run_simulation():
    pkdp('RUN SIM')
    exec(pkio.read_text(template_common.PARAMETERS_PYTHON_FILE), locals(), locals())
