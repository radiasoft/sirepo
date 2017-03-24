# -*- coding: utf-8 -*-
"""Wrapper to run Hellweg2D from the command line.

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkio
from pykern.pkdebug import pkdp, pkdc
from rslinac.solver import BeamSolver
from sirepo import simulation_db
from sirepo.template import template_common
import sirepo.template.hellweg2d as template

def run(cfg_dir):
    """Run Hellweg2D in ``cfg_dir``

    Args:
        cfg_dir (str): directory to run hellweg2d in
    """
    _run_hellweg2d(cfg_dir)
    data = simulation_db.read_json(template_common.INPUT_BASE_NAME)
    report = data['models'][data['report']]
    res = None
    if data['report'] == 'beamReport':
        res = template.extract_beam_report(report, cfg_dir, 0)
    elif data['report'] == 'beamHistogramReport':
        res = template.extract_beam_histrogram(report, cfg_dir, 0)
    else:
        raise RuntimeError('unknown report: {}'.format(data['report']))
    simulation_db.write_result(res)


def run_background(cfg_dir):
    _run_hellweg2d(cfg_dir)
    simulation_db.write_result({})


def _run_hellweg2d(cfg_dir):
    with pkio.save_chdir(cfg_dir):
        exec(pkio.read_text(template_common.PARAMETERS_PYTHON_FILE), locals(), locals())
        pkio.write_text('input.txt', input_file)
        #TODO(pjm): get ini values from template
        pkio.write_text('defaults.ini', '')
        solver = BeamSolver('defaults.ini', 'input.txt')
        solver.solve()
        #TODO(pjm): save output to known filename
        solver.save_output('output.txt')
        solver.dump_bin(template.HELLWEG2D_DUMP_FILE)
