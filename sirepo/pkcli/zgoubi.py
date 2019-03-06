# -*- coding: utf-8 -*-
"""Wrapper to run zgoubi from the command line.

:copyright: Copyright (c) 2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkio
from pykern.pkdebug import pkdp, pkdc
from sirepo import simulation_db
from sirepo.template import template_common
import py.path
import re
import sirepo.template.zgoubi as template
import subprocess

_EXE_PATH = 'zgoubi'

_TWISS_TO_BUNCH_FIELD = {
    'btx': 'beta_Y',
    'alfx': 'alpha_Y',
    'Dx': 'DY',
    'Dxp': 'DT',
    'bty': 'beta_Z',
    'alfy': 'alpha_Z',
    'Dy': 'DZ',
    'Dyp': 'DP',
}

_ZGOUBI_FIT_FILE = 'zgoubi.FIT.out.dat'


def run(cfg_dir):
    data = _bunch_match_twiss(cfg_dir)
    _run_zgoubi(cfg_dir)
    template.save_report_data(data, py.path.local(cfg_dir))


def _bunch_match_twiss(cfg_dir):
    data = simulation_db.read_json(template_common.INPUT_BASE_NAME)
    bunch = data.models.bunch
    if bunch.match_twiss_parameters == '1' and ('bunchReport' in data.report or data.report == 'animation'):
        report = data['report']
        data['report'] = 'twissReport2'
        template.write_parameters(data, py.path.local(cfg_dir), False, 'twiss.py')
        _run_zgoubi(cfg_dir, python_file='twiss.py')
        col_names, row = template.extract_first_twiss_row(cfg_dir)
        for f in _TWISS_TO_BUNCH_FIELD.keys():
            v = template.column_data(f, col_names, [row])[0]
            bunch[_TWISS_TO_BUNCH_FIELD[f]] = v
            if f == 'btx' or f == 'bty':
                assert v > 0, 'invalid twiss parameter: {} <= 0'.format(f)
        found_fit = False
        lines = pkio.read_text(_ZGOUBI_FIT_FILE).split('\n')
        for i in xrange(len(lines)):
            line = lines[i]
            if re.search(r"^\s*'OBJET'", line):
                values = lines[i + 4].split()
                assert len(values) >= 5
                found_fit = True
                bunch['Y0'] = float(values[0]) * 1e-2
                bunch['T0'] = float(values[1]) * 1e-3
                break
        assert found_fit, 'failed to parse fit parameters'
        simulation_db.write_json(py.path.local(cfg_dir).join(template.BUNCH_SUMMARY_FILE), bunch)
        data['report'] = report
        # rewrite the original report with original parameters
        template.write_parameters(data, py.path.local(cfg_dir), False)
    return data


def run_background(cfg_dir):
    res = {}
    data = simulation_db.read_json(template_common.INPUT_BASE_NAME)
    try:
        _bunch_match_twiss(cfg_dir)
        _run_zgoubi(cfg_dir)
    except Exception as e:
        res = {
            'error': str(e),
        }
    simulation_db.write_result(res)


def _run_zgoubi(cfg_dir, python_file=template_common.PARAMETERS_PYTHON_FILE):
    with pkio.save_chdir(cfg_dir):
        exec(pkio.read_text(python_file), locals(), locals())
        subprocess.call([_EXE_PATH])
