# -*- coding: utf-8 -*-
"""Wrapper to run synergia from the command line.

:copyright: Copyright (c) 2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkio
from pykern.pkdebug import pkdp, pkdc
from sirepo import mpi
from sirepo import simulation_db
from sirepo.template import template_common
import py.path
import re
import sirepo.template.synergia as template

_SCHEMA = simulation_db.get_schema(template.SIM_TYPE)


def run(cfg_dir):
    data = simulation_db.read_json(template_common.INPUT_BASE_NAME)
    report = data['report']
    if 'bunchReport' in report or report == 'twissReport' or report == 'twissReport2':
        template_common.exec_parameters()
        template.save_report_data(data, py.path.local(cfg_dir))
    else:
        raise AssertionError('unknown report: {}'.format(report))


def run_background(cfg_dir):
    data = simulation_db.read_json(template_common.INPUT_BASE_NAME)
    distribution = data['models']['bunch']['distribution']
    run_with_mpi = distribution == 'lattice' or distribution == 'file'
    if run_with_mpi:
        template_common.exec_parameters_with_mpi()
    else:
        #TODO(pjm): MPI doesn't work with rsbeams distributions yet
        template_common.exec_parameters()
