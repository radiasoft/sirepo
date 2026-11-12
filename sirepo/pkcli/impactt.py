# -*- coding: utf-8 -*-
"""Wrapper to run impact from the command line.
:copyright: Copyright (c) 2024 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from sirepo import simulation_db
from sirepo.template import template_common
import pykern.pkio
import sirepo.template.impactt as template

# no run_background() because template.impactt.write_parameters() returns a run command


def run(cfg_dir):
    template_common.exec_parameters()
    data = simulation_db.read_json(template_common.INPUT_BASE_NAME)
    template.save_sequential_report_data(data, pykern.pkio.py_path(cfg_dir))
