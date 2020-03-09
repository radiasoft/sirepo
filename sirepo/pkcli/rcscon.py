# -*- coding: utf-8 -*-
"""Wrapper to run RCSCON from the command line.

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkio
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdc, pkdlog
from sirepo import simulation_db
from sirepo.template import template_common
import pykern.pkio
import sirepo.template.rcscon as template
import pykern.pkrunpy


def run(cfg_dir):
    with pkio.save_chdir(cfg_dir) as d:
        _run_simulation()
        template.extract_report_data(
            d,
            simulation_db.read_json(template_common.INPUT_BASE_NAME),
        )


def run_background(cfg_dir):
    res = PKDict()
    with pkio.save_chdir(cfg_dir):
        try:
            _run_simulation()
        except Exception as e:
            res.error = str(e)
        simulation_db.write_result(res)


def _run_simulation():
    pykern.pkrunpy.run_path_as_module(template_common.PARAMETERS_PYTHON_FILE)
