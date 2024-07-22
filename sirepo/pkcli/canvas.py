# -*- coding: utf-8 -*-
"""Wrapper to run canvas from the command line.

:copyright: Copyright (c) 2024 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern import pkio
from pykern.pkdebug import pkdp, pkdc, pkdlog
from sirepo import simulation_db
from sirepo.template import template_common
import sirepo.template.canvas as template


def run(cfg_dir):
    template_common.exec_parameters(template.DISTRIBUTION_PYTHON_FILE)
    data = simulation_db.read_json(template_common.INPUT_BASE_NAME)
    template.save_sequential_report_data(pkio.py_path(cfg_dir), data)
