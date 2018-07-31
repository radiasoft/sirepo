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
import h5py
import numpy as np
import py.path
import sirepo.template.synergia as template

_SCHEMA = simulation_db.get_schema(template.SIM_TYPE)


def run(cfg_dir):
    data = simulation_db.read_json(template_common.INPUT_BASE_NAME)
    report = data['report']
    if report == 'bunchReport' or report == 'twissReport' or report == 'twissReport2':
        try:
            with pkio.save_chdir(cfg_dir):
                exec(pkio.read_text(template_common.PARAMETERS_PYTHON_FILE), locals(), locals())
            if report == 'bunchReport':
                res = _run_bunch_report(data)
            else:
                res = _run_twiss_report(data, report)
        except Exception as e:
            res = template.parse_error_log(py.path.local(cfg_dir)) or {
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


def _run_bunch_report(data):
    import synergia.bunch
    with h5py.File(template.OUTPUT_FILE['twissReport'], 'r') as f:
        twiss0 = dict(map(
            lambda k: (k, template.format_float(f[k][0])),
            ('alpha_x', 'alpha_y', 'beta_x', 'beta_y'),
        ))
    report = data.models[data['report']]
    bunch = data.models.bunch
    if bunch.distribution == 'file':
        bunch_file = template_common.lib_file_name('bunch', 'particleFile', bunch.particleFile)
    else:
        bunch_file = template.OUTPUT_FILE['bunchReport']

    with h5py.File(bunch_file, 'r') as f:
        x = f['particles'][:, getattr(synergia.bunch.Bunch, report['x'])]
        y = f['particles'][:, getattr(synergia.bunch.Bunch, report['y'])]
    hist, edges = np.histogramdd([x, y], template_common.histogram_bins(report['histogramBins']))
    return {
        'title': '{}-{}'.format(report['x'], report['y']),
        'x_range': [float(edges[0][0]), float(edges[0][-1]), len(hist)],
        'y_range': [float(edges[1][0]), float(edges[1][-1]), len(hist[0])],
        'x_label': template.label(report['x']),
        'y_label': template.label(report['y']),
        'z_matrix': hist.T.tolist(),
        'summaryData': {
            'bunchTwiss': twiss0,
        },
    }


def _run_twiss_report(data, report_name):
    x = None
    plots = []
    report = data['models'][report_name]
    with h5py.File(template.OUTPUT_FILE[report_name], 'r') as f:
        x = f['s'][:].tolist()
        for yfield in ('y1', 'y2', 'y3'):
            if report[yfield] == 'none':
                continue
            name = report[yfield]
            plots.append({
                'name': name,
                'label': template.label(report[yfield], _SCHEMA['enum']['TwissParameter']),
                'points': f[name][:].tolist(),
            })
    return {
        'title': '',
        'x_range': [min(x), max(x)],
        'y_range': template_common.compute_plot_color_and_range(plots),
        'x_label': 's [m]',
        'y_label': '',
        'x_points': x,
        'plots': plots,
    }
