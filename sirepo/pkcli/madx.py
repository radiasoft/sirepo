# -*- coding: utf-8 -*-
"""Wrapper to run MAD-X from the command line.

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkio
from pykern import pksubprocess
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdc, pkdlog
from sirepo import mpi
from sirepo import simulation_db
from sirepo.template import template_common, madx_parser
import sirepo.sim_data
import sirepo.template.madx as template

_SIM_DATA = sirepo.sim_data.get_class('madx')


def run(cfg_dir):
    _run_madx()
    template.save_sequential_report_data(
        simulation_db.read_json(template_common.INPUT_BASE_NAME),
        pkio.py_path(cfg_dir),
    )

def run_background(cfg_dir):
    _run_madx()

def _run_madx():
    pksubprocess.check_call_with_signals(
        ['madx', template.MADX_INPUT_FILE],
        msg=pkdlog,
        output=template.MADX_OUTPUT_FILE,
    )
