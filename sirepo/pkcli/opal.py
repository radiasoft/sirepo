# -*- coding: utf-8 -*-
"""Wrapper to run OPAL from the command line.

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkio
from pykern import pksubprocess
from pykern.pkdebug import pkdp, pkdc, pkdlog
from sirepo import simulation_db
from sirepo.template import template_common
import sirepo.template.opal as template
import re

_SCHEMA = simulation_db.get_schema(template.SIM_TYPE)


def run(cfg_dir):
    with pkio.save_chdir(cfg_dir):
        data = simulation_db.read_json(template_common.INPUT_BASE_NAME)
        pksubprocess.check_call_with_signals(['opal', 'opal.in'], msg=pkdlog)
        if data['report'] == 'twissReport':
            simulation_db.write_result(_extract_twiss_report(data))


def run_background(cfg_dir):
    data = simulation_db.read_json(template_common.INPUT_BASE_NAME)
    with pkio.save_chdir(cfg_dir):
        pksubprocess.check_call_with_signals(['opal', 'opal.in'], msg=pkdlog)
    simulation_db.write_result({})


def _column_data(col, col_names, rows):
    idx = col_names.index(col)
    assert idx >= 0, 'invalid col: {}'.format(col)
    res = []
    for row in rows:
        res.append(float(row[idx]))
    return res


def _extract_twiss_report(data):
    report = data['models'][data['report']]
    report['x'] = 's'
    report['y1'] = 'betx'
    report['y2'] = 'bety'
    report['y3'] = 'dx'
    #TODO(pjm): global twiss file name
    col_names, rows = _read_data_file('out.twiss')
    x = _column_data(report['x'], col_names, rows)
    y_range = None
    plots = []
    for f in ('y1', 'y2', 'y3'):
        if report[f] == 'none':
            continue
        plots.append({
            'points': _column_data(report[f], col_names, rows),
            'label': '{}'.format(report[f]),
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


def _read_data_file(path):
    col_names = []
    rows = []
    with pkio.open_text(str(path)) as f:
        col_names = []
        rows = []
        mode = ''
        for line in f:
            if '---' in line:
                if mode == 'header':
                    mode = 'data'
                elif mode == 'data':
                    break
                if not mode:
                    mode = 'header'
                continue
            line = re.sub('\0', '', line)
            if mode == 'header':
                col_names = re.split('\s+', line.lower())
            elif mode == 'data':
                #TODO(pjm): separate overlapped columns. Instead should explicitly set field dimensions
                line = re.sub('(\d)(\-\d)', r'\1 \2', line)
                line = re.sub(r'(\.\d{3})(\d+\.)', r'\1 \2', line)
                rows.append(re.split('\s+', line))
    return col_names, rows
