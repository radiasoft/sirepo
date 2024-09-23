# -*- coding: utf-8 -*-
"""Wrapper to run ImpactX from the command line.
:copyright: Copyright (c) 2024 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern import pkio
from sirepo import simulation_db
from sirepo.template import template_common
import sirepo.template.impactx


def run(cfg_dir):
    template_common.exec_parameters()
    sirepo.template.impactx.save_sequential_report_data(
        pkio.py_path(cfg_dir),
        simulation_db.read_json(template_common.INPUT_BASE_NAME),
    )


# no run_background() because template.impactx.write_parameters() returns a run command
