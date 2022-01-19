# -*- coding: utf-8 -*-
"""Wrapper to run controls code from the command line.

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkio, pkjson
from pykern.pkcollections import PKDict
from sirepo.template import template_common
import sirepo.template.controls as template
from sirepo import simulation_db


def run(cfg_dir):
    template_common.exec_parameters()
    d = pkio.py_path(cfg_dir)
    template_common.write_sequential_result(
        PKDict(
            elementValues=template._read_summary_line(
                d,
                simulation_db.get_schema(template.SIM_TYPE).constants.maxBPMPoints,
            )
        ),
        run_dir=d,
    )


def run_background(cfg_dir):
    # TODO (gurhar1133): need to generate ptc_particles.madx like pkcli.madx.run_background
    # from pykern import pkio
    pkio.py_path('~/ptc_particles.madx').copy(pkio.py_path(cfg_dir).join('ptc_particles.madx'))
    template_common.exec_parameters()
