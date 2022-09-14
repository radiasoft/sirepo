# -*- coding: utf-8 -*-
"""Wrapper to run activait from the command line.

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdc, pkdlog
from sirepo import simulation_db
from sirepo.template import template_common
import py.path
import sirepo.template.activait as template


def run(cfg_dir):
    template_common.exec_parameters()
    data = simulation_db.read_json(template_common.INPUT_BASE_NAME)
    template.save_sequential_report_data(py.path.local(cfg_dir), data)


def run_background(cfg_dir):
    template_common.exec_parameters()
