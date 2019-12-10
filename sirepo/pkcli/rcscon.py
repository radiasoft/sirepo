# -*- coding: utf-8 -*-
"""Wrapper to run RCSCON from the command line.

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkio
from pykern.pkdebug import pkdp, pkdc, pkdlog
from sirepo import simulation_db
from sirepo.template import template_common
import py.path
import sirepo.template.rcscon as template


def run(cfg_dir):
    with pkio.save_chdir(cfg_dir):
        _run_simulation()
        data = simulation_db.read_json(template_common.INPUT_BASE_NAME)
        template.extract_report_data(py.path.local(cfg_dir), data)


def run_background(cfg_dir):
    with pkio.save_chdir(cfg_dir):
        _run_simulation()
        simulation_db.write_result({})


def _run_simulation():
    exec(pkio.read_text(template_common.PARAMETERS_PYTHON_FILE), locals(), locals())
