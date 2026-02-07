# -*- coding: utf-8 -*-
"""Wrapper to run myapp from the command line.

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern import pksubprocess
from pykern.pkdebug import pkdp, pkdc, pkdlog
from sirepo import simulation_db
from sirepo.template import template_common
import sirepo.template.myapp as template
import sys


def run(cfg_dir):
    _run_python()
    data = simulation_db.read_json(template_common.INPUT_BASE_NAME)
    if data.report == "heightWeightReport":
        res = template.report_from_csv(
            "Dog Height and Weight Over Time",
            ("height", "weight"),
        )
    else:
        raise AssertionError("unknown report: {}".format(data.report))
    template_common.write_sequential_result(res)


def run_background(cfg_dir):
    _run_python()


def _run_python():
    pksubprocess.check_call_with_signals(
        [sys.executable, template_common.PARAMETERS_PYTHON_FILE],
    )
