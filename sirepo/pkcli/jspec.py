# -*- coding: utf-8 -*-
"""Wrapper to run JSPEC from the command line.

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkio
from pykern import pksubprocess
from pykern.pkdebug import pkdp, pkdc, pkdlog
from sirepo import simulation_db
from sirepo.template import sdds_util, template_common
import os.path
import re
import sirepo.template.jspec as template

def run(cfg_dir):
    with pkio.save_chdir(cfg_dir):
        data = simulation_db.read_json(template_common.INPUT_BASE_NAME)
        if data['report'] == 'twissReport':
            simulation_db.write_result(_extract_twiss_report(data))
        elif data['report'] == 'rateCalculationReport':
            text = _run_jspec(data)
            res = {
                #TODO(pjm): x_range is needed for sirepo-plotting.js, need a better valid-data check
                'x_range': [],
                'rate': [],
            }
            for line in text.split("\n"):
                m = re.match(r'^(.*? rate.*?)\:\s+(\S+)\s+(\S+)\s+(\S+)', line)
                if m:
                    row = [m.group(1), [m.group(2), m.group(3), m.group(4)]]
                    row[0] = re.sub('\(', '[', row[0]);
                    row[0] = re.sub('\)', ']', row[0]);
                    res['rate'].append(row)
            simulation_db.write_result(res)
        else:
            assert False, 'unknown report: {}'.format(data['report'])


def run_background(cfg_dir):
    with pkio.save_chdir(cfg_dir):
        _run_jspec(simulation_db.read_json(template_common.INPUT_BASE_NAME))
        simulation_db.write_result({})


def _elegant_to_madx(ring):
    # if the lattice source is an elegant twiss file, convert it to MAD-X format
    if ring['latticeSource'] == 'madx':
        return template_common.lib_file_name('ring', 'lattice', ring['lattice'])
    if ring['latticeSource'] == 'elegant':
        elegant_twiss_file = template_common.lib_file_name('ring', 'elegantTwiss', ring['elegantTwiss'])
    else: # elegant-sirepo
        if 'elegantSirepo' not in ring or not ring['elegantSirepo']:
            raise RuntimeError('elegant simulation not selected')
        elegant_twiss_file = template.ELEGANT_TWISS_FILENAME
        if not os.path.exists(elegant_twiss_file):
            raise RuntimeError('elegant twiss output unavailable. Run elegant simulation.')
    sdds_util.twiss_to_madx(elegant_twiss_file, template.JSPEC_TWISS_FILENAME)
    return template.JSPEC_TWISS_FILENAME


_X_FIELD = 's'

_FIELD_UNITS = {
    'betx': 'm',
    #'alfx': '',
    'mux': 'rad/2π',
    'dx': 'm',
    #'dpx': '',
    'bety': 'm',
    #'alfy': '',
    'muy': 'rad/2π',
    'dx': 'm',
    #'dpx': '',
}

def _extract_twiss_report(data):
    report = data['models'][data['report']]
    report['x'] = _X_FIELD
    values = _parse_madx(_elegant_to_madx(data['models']['ring']))
    x = _float_list(values[report['x']])
    y_range = None
    plots = []
    for f in ('y1', 'y2', 'y3'):
        if report[f] == 'none':
            continue
        plots.append({
            'points': _float_list(values[report[f]]),
            'label': '{} [{}]'.format(report[f], _FIELD_UNITS[report[f]]) if report[f] in _FIELD_UNITS else report[f],
        })
    return {
        'title': '',
        'x_range': [min(x), max(x)],
        'y_label': '',
        'x_label': '{} [{}]'.format(report['x'], 'm'),
        'x_points': x,
        'plots': plots,
        'y_range': template_common.compute_plot_color_and_range(plots),
    }


def _float_list(ar):
    return map(lambda x: float(x), ar)


def _run_jspec(data):
    _elegant_to_madx(data['models']['ring'])
    exec(pkio.read_text(template_common.PARAMETERS_PYTHON_FILE), locals(), locals())
    jspec_filename = template.JSPEC_INPUT_FILENAME
    pkio.write_text(jspec_filename, jspec_file)
    pksubprocess.check_call_with_signals(['jspec', jspec_filename], msg=pkdlog, output=template.JSPEC_LOG_FILE)
    return pkio.read_text(template.JSPEC_LOG_FILE)


def _parse_madx(tfs_file):
    text = pkio.read_text(tfs_file)
    mode = 'header'
    col_names = []
    rows = []
    for line in text.split("\n"):
        if mode == 'header':
            # header row starts with *
            if re.search('^\*\s', line):
                col_names = re.split('\s+', line)
                col_names = col_names[1:]
                mode = 'data'
        elif mode == 'data':
            # data rows after header, start with blank
            if re.search('^\s+\S', line):
                data = re.split('\s+', line)
                rows.append(data[1:])
    res = dict(map(lambda x: (x.lower(), []), col_names))
    for i in range(len(col_names)):
        name = col_names[i].lower()
        if name:
            for row in rows:
                res[name].append(row[i])
    return res
