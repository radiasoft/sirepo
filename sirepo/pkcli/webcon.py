# -*- coding: utf-8 -*-
"""Wrapper to run myapp from the command line.

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkio
from pykern.pkdebug import pkdp, pkdc, pkdlog
from sirepo import simulation_db
from sirepo.template import template_common
import py.path
import sirepo.template.webcon as template


_SCHEMA = simulation_db.get_schema(template.SIM_TYPE)


def run(cfg_dir):
    with pkio.save_chdir(cfg_dir):
        data = simulation_db.read_json(template_common.INPUT_BASE_NAME)
        if data.report == 'analysisReport':
            res = template.get_analysis_report(py.path.local(cfg_dir), data)
        elif data['report'] == 'fftReport':
            res = template.get_fft(py.path.local(cfg_dir), data)
        else:
            assert False, 'unknown report: {}'.format(data.report)
        simulation_db.write_result(res)


def run_background(cfg_dir):
    with pkio.save_chdir(cfg_dir):
        simulation_db.write_result({})
