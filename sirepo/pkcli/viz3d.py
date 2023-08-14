# -*- coding: utf-8 -*-
"""Wrapper to run epicsllrf from the command line.

:copyright: Copyright (c) 2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkcollections import PKDict
from sirepo import simulation_db
from sirepo.template import template_common
import py.path


def run(cfg_dir):
    template_common.exec_parameters()
    data = simulation_db.read_json(template_common.INPUT_BASE_NAME)
    template.save_sequential_report_data(py.path.local(cfg_dir), data)
