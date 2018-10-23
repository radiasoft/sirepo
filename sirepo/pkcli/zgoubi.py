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
import sirepo.template.zgoubi as template
import subprocess

_SCHEMA = simulation_db.get_schema(template.SIM_TYPE)

#TODO(pjm): change to 'zgoubi' when available in container
_EXE_PATH = '/home/vagrant/bin/zgoubi'

_REPORT_INFO = {
    'twissReport': ['zgoubi.TWISS.out', 'TwissParameter', 'sums'],
    'opticsReport': ['zgoubi.OPTICS.out', 'OpticsParameter', 'cumulsm'],
}


def run(cfg_dir):
    data = simulation_db.read_json(template_common.INPUT_BASE_NAME)
    report = data['report']
    if report == 'twissReport' or report == 'opticsReport':
        _run_zgoubi(cfg_dir)
        res = _extract_plot(data, report)
    else:
        raise RuntimeError('unknown report: {}'.format(report))
    simulation_db.write_result(res)


def run_background(cfg_dir):
    res = {}
    data = simulation_db.read_json(template_common.INPUT_BASE_NAME)
    try:
        _run_zgoubi(cfg_dir)
    except Exception as e:
        res = {
            'error': str(e),
        }
    simulation_db.write_result(res)


def _extract_plot(data, report_name):
    filename, enum_name, x_field = _REPORT_INFO[report_name]
    report = data['models'][report_name]
    plots = []
    col_names, rows = template.read_data_file(filename)
    for f in ('y1', 'y2', 'y3'):
        if report[f] == 'none':
            continue
        plots.append({
            'points': template.column_data(report[f], col_names, rows),
            'label': template_common.enum_text(_SCHEMA, enum_name, report[f]),
        })
    x = template.column_data(x_field, col_names, rows)
    return {
        'title': '',
        'x_range': [min(x), max(x)],
        'y_label': '',
        'x_label': 's [m]',
        'x_points': x,
        'plots': plots,
        'y_range': template_common.compute_plot_color_and_range(plots),
    }


def _run_zgoubi(cfg_dir):
    with pkio.save_chdir(cfg_dir):
        exec(pkio.read_text(template_common.PARAMETERS_PYTHON_FILE), locals(), locals())
        subprocess.call([_EXE_PATH])
