# -*- coding: utf-8 -*-
"""Wrapper to run Hellweg from the command line.

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkio
from pykern.pkdebug import pkdp, pkdc
from rslinac import solver
from sirepo import simulation_db
from sirepo.template import template_common
import py.path
import sirepo.template.hellweg as template

def run(cfg_dir):
    """Run Hellweg in ``cfg_dir``

    Args:
        cfg_dir (str): directory to run hellweg in
    """
    _run_hellweg(cfg_dir)
    data = simulation_db.read_json(template_common.INPUT_BASE_NAME)
    report = data['models'][data['report']]
    res = None
    if data['report'] == 'beamReport':
        res = template.extract_beam_report(report, py.path.local(cfg_dir), 0)
    elif data['report'] == 'beamHistogramReport':
        res = template.extract_beam_histrogram(report, py.path.local(cfg_dir), 0)
    else:
        raise RuntimeError('unknown report: {}'.format(data['report']))
    simulation_db.write_result(res)


def run_background(cfg_dir):
    _run_hellweg(cfg_dir)
    simulation_db.write_result({})


def _run_hellweg(cfg_dir):
    with pkio.save_chdir(cfg_dir):
        exec(pkio.read_text(template_common.PARAMETERS_PYTHON_FILE), locals(), locals())
        pkio.write_text(template.HELLWEG_INPUT_FILE, input_file)
        pkio.write_text(template.HELLWEG_INI_FILE, ini_file)
        s = solver.BeamSolver(template.HELLWEG_INI_FILE, template.HELLWEG_INPUT_FILE)
        s.solve()
        s.save_output(template.HELLWEG_SUMMARY_FILE)
        s.dump_bin(template.HELLWEG_DUMP_FILE)
