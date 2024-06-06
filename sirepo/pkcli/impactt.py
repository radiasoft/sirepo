# -*- coding: utf-8 -*-
"""Wrapper to run impact from the command line.
:copyright: Copyright (c) 2024 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkcollections import PKDict
from pykern import pksubprocess
from sirepo import simulation_db
from sirepo.template import template_common
import py.path
import sys


def run(cfg_dir):
    pksubprocess.check_call_with_signals(
        [sys.executable, template_common.PARAMETERS_PYTHON_FILE],
    )
    data = simulation_db.read_json(template_common.INPUT_BASE_NAME)
    template_common.write_sequential_result(data)
