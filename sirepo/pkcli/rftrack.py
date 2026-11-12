# -*- coding: utf-8 -*-
"""Wrapper to run RF-Track from the command line.

:copyright: Copyright (c) 2026 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from sirepo import simulation_db
from sirepo.template import template_common
import pykern.pkio
import sirepo.template.rftrack as template

# no run_background() work beyond exec_parameters(); write_parameters()
# already rendered the correct script for either report type


def run(cfg_dir):
    template_common.exec_parameters()
    data = simulation_db.read_json(template_common.INPUT_BASE_NAME)
    template.save_sequential_report_data(data, pykern.pkio.py_path(cfg_dir))


def run_background(cfg_dir):
    template_common.exec_parameters()
