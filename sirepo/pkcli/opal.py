# -*- coding: utf-8 -*-
"""Wrapper to run OPAL from the command line.

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkio
from pykern import pksubprocess
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdc, pkdlog
from sirepo import simulation_db
from sirepo.template import template_common
import py.path
import re
import sirepo.mpi
import sirepo.template.opal as template


def run(cfg_dir):
    run_opal()
    data = simulation_db.read_json(template_common.INPUT_BASE_NAME)
    if "bunchReport" in data.report or data.report == "twissReport":
        template.save_sequential_report_data(data, py.path.local(cfg_dir))


def run_background(cfg_dir):
    run_opal(with_mpi=True, compute_positions=True)


def run_opal(with_mpi=False, compute_positions=False):
    if with_mpi and sirepo.mpi.cfg().cores < 2:
        with_mpi = False
    if with_mpi:
        sirepo.mpi.run_program(
            ["opal", template.OPAL_INPUT_FILE],
            output=template.OPAL_OUTPUT_FILE,
        )
    else:
        pksubprocess.check_call_with_signals(
            ["opal", template.OPAL_INPUT_FILE],
            output=template.OPAL_OUTPUT_FILE,
            msg=pkdlog,
        )
    if compute_positions:
        template_common.exec_parameters(template.OPAL_POSITION_FILE)
