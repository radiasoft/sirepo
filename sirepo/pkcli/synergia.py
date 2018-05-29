# -*- coding: utf-8 -*-
"""Wrapper to run myapp from the command line.

:copyright: Copyright (c) 2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkio
from pykern.pkdebug import pkdp, pkdc
from sirepo import simulation_db
from sirepo.template import template_common
import numpy as np
import sirepo.template.synergia as template

#TODO(pjm): combine from template/synergia and template/elegant and put in template_common
_PLOT_LINE_COLOR = {
    'y1': '#1f77b4',
    'y2': '#ff7f0e',
    'y3': '#2ca02c',
}

_SCHEMA = simulation_db.get_schema(template.SIM_TYPE)


def run(cfg_dir):
    data = simulation_db.read_json(template_common.INPUT_BASE_NAME)
    report = data['report']
    if report == 'bunchReport' or report == 'twissReport':
        try:
            with pkio.save_chdir(cfg_dir):
                exec(pkio.read_text(template_common.PARAMETERS_PYTHON_FILE), locals(), locals())
            # bunch or twiss variable comes from parameter file exec() above
            if report == 'bunchReport':
                res = _run_bunch_report(data, bunch, twiss)
            else:
                res = _run_twiss_report(data, twiss)
        except Exception as e:
            res = {
                'error': str(e),
            }
        simulation_db.write_result(res)
    else:
        raise RuntimeError('unknown report: {}'.format(report))


def run_background(cfg_dir):
    res = {}
    try:
        with pkio.save_chdir(cfg_dir):
            exec(pkio.read_text(template_common.PARAMETERS_PYTHON_FILE), locals(), locals())
    except Exception as e:
        res = {
            'error': str(e),
        }
    simulation_db.write_result(res)


def _run_bunch_report(data, bunch, twiss):
    twiss0 = twiss[0]
    report = data.models[data['report']]
    particles = bunch.get_local_particles()
    x = particles[:, getattr(bunch, report['x'])]
    y = particles[:, getattr(bunch, report['y'])]
    hist, edges = np.histogramdd([x, y], template_common.histogram_bins(200))
    return {
        'x_range': [float(edges[0][0]), float(edges[0][-1]), len(hist)],
        'y_range': [float(edges[1][0]), float(edges[1][-1]), len(hist[0])],
        'x_label': _label(report['x']),
        'y_label': _label(report['y']),
        'title': '{}-{}'.format(report['x'], report['y']),
        'z_matrix': hist.T.tolist(),
        'summaryData': {
            'bunchTwiss': {
                'alpha_x': template.format_float(twiss0['alpha_x']),
                'alpha_y': template.format_float(twiss0['alpha_y']),
                'beta_x': template.format_float(twiss0['beta_x']),
                'beta_y': template.format_float(twiss0['beta_y']),
            },
        },
    }


def _run_twiss_report(data, twiss):
    plots = []
    report = data['models']['twissReport']
    x = []
    plots = []
    y_range = None
    for yfield in ('y1', 'y2', 'y3'):
        if report[yfield] != 'none':
            plots.append({
                'name': report[yfield],
                'points': [],
                'label': report[yfield],
                'color': _PLOT_LINE_COLOR[yfield],
            })
    for row in twiss:
        x.append(row['s'])
        for plot in plots:
            v = row[plot['name']]
            plot['points'].append(v)
            if y_range:
                if v < y_range[0]:
                    y_range[0] = v
                if v > y_range[1]:
                    y_range[1] = v
            else:
                y_range = [v, v]
    return {
        'title': '',
        'x_range': [min(x), max(x)],
        'y_label': '',
        'x_label': 's [m]',
        'x_points': x,
        'plots': plots,
        'y_range': y_range,
    }


_UNITS = {
    'x': 'm',
    'y': 'm',
    'cdt': 'm',
}

def _label(v):
    if v not in _UNITS:
        return v
    return '{} [{}]'.format(v, _UNITS[v])
