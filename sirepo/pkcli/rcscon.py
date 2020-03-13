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


def run(cfg_dir):
    template_common.exec_parameters()
    template.extract_report_data(
        d,
        simulation_db.read_json(template_common.INPUT_BASE_NAME),
    )


def run_background(cfg_dir):
    res = PKDict()
    try:
        template_common.exec_parameters()
    except Exception as e:
        res.error = str(e)
    simulation_db.write_result(res)


def _run_simulation():
