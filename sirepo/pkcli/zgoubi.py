# -*- coding: utf-8 -*-
"""Wrapper to run zgoubi from the command line.

:copyright: Copyright (c) 2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkio
from pykern.pkdebug import pkdp, pkdc, pkdlog
from sirepo import simulation_db
from sirepo.template import template_common
import os
import py.path
import re
import sirepo.template.zgoubi as template
import subprocess

_EXE_PATH = 'zgoubi'
_MAX_OUTPUT_SIZE = 5e7
_TUNES_PATH = 'tunesFromFai'

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
    data = simulation_db.read_json(template_common.INPUT_BASE_NAME)
    report = data['report']
    if report == 'tunesReport':
        _run_tunes_report(cfg_dir, data)
        return
    # bunchReport, twissReport and twissReport2
    _bunch_match_twiss(cfg_dir, data)
    _run_zgoubi(cfg_dir)
    template.save_report_data(data, py.path.local(cfg_dir))


def run_background(cfg_dir):
    res = {}
    data = simulation_db.read_json(template_common.INPUT_BASE_NAME)
    _validate_estimate_output_file_size(data, res)
    if 'error' not in res:
        try:
            _bunch_match_twiss(cfg_dir, data)
            _run_zgoubi(cfg_dir)
            res['frame_count'] = template.read_frame_count(py.path.local(cfg_dir))
        except Exception as e:
            res['error'] = str(e)
    simulation_db.write_result(res)


def _beamline_steps(beamline_map, element_map, beamline_id):
    res = 0
    for item_id in beamline_map[beamline_id]['items']:
        if item_id in beamline_map:
            res += _beamline_steps(beamline_map, element_map, item_id)
            continue
        el = element_map[item_id]
        if el.get('IL', '0') != '1':
            continue
        xpas = str(el.XPAS)
        if re.search(r'\#', xpas):
            xpas = re.sub(r'^#', '', xpas)
            res += int(xpas.split('|')[1])
        elif 'l' in el:
            res += int(el.l / float(xpas))
        else:
            # no length (tosca?)
            res += 0
    return res


def _bunch_match_twiss(cfg_dir, data):
    bunch = data.models.bunch
    if bunch.match_twiss_parameters == '1' and ('bunchReport' in data.report or data.report == 'animation'):
        report = data['report']
        data['report'] = 'twissReport2'
        template.write_parameters(data, py.path.local(cfg_dir), False, 'twiss.py')
        _run_zgoubi(cfg_dir, python_file='twiss.py')
        col_names, row = template.extract_first_twiss_row(cfg_dir)
        for f in _TWISS_TO_BUNCH_FIELD.keys():
            v = template.column_data(f, col_names, [row])[0]
            if (f == 'btx' or f == 'bty') and v <= 0:
                pkdlog('invalid calculated twiss parameter: {} <= 0', f)
                v = 1.0
            bunch[_TWISS_TO_BUNCH_FIELD[f]] = v
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


def _validate_estimate_output_file_size(data, res):
    bunch = data.models.bunch
    count = bunch.particleCount
    if bunch.method == 'OBJET2.1':
        count = bunch.particleCount2
    settings = data.models.simulationSettings
    line_size = 800
    fai_size = line_size * settings.npass / (settings.ip or 1) * float(count)
    if fai_size > _MAX_OUTPUT_SIZE:
        res['error'] = 'Estimated FAI output too large.\nReduce particle count or number of runs,\nor increase diagnostic interval.'
        return
    beamline_map = {}
    for bl in data.models.beamlines:
        beamline_map[bl.id] = bl
    element_map = {}
    for el in data.models.elements:
        element_map[el._id] = el
    steps = _beamline_steps(beamline_map, element_map, data.models.simulation.visualizationBeamlineId)
    plt_size = line_size * steps * settings.npass * float(count)
    if plt_size > _MAX_OUTPUT_SIZE:
        res['error'] = 'Estimated PLT output too large.\nReduce particle count, number of runs, element integration step size\nor decrease elements with plotting enabled.'


def _run_tunes_report(cfg_dir, data):
    with pkio.save_chdir(cfg_dir):
        exec(pkio.read_text(template_common.PARAMETERS_PYTHON_FILE), locals(), locals())
        pkio.write_text(template.TUNES_INPUT_FILE, tunes_file)
        #TODO(pjm): uses datafile from animation directory
        os.symlink('../animation/zgoubi.fai', 'zgoubi.fai')
        subprocess.call([_TUNES_PATH])
        simulation_db.write_result(template.extract_tunes_report(cfg_dir, data))


def _run_zgoubi(cfg_dir, python_file=template_common.PARAMETERS_PYTHON_FILE):
    with pkio.save_chdir(cfg_dir):
        exec(pkio.read_text(python_file), locals(), locals())
        subprocess.call([_EXE_PATH])
