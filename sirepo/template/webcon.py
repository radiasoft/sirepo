# -*- coding: utf-8 -*-
u"""Webcon execution template.

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkcollections
from pykern import pkio
from pykern import pkjinja
from pykern.pkdebug import pkdc, pkdp
from scipy.optimize import curve_fit
import sympy as sp
from sirepo import simulation_db
from sirepo.template import template_common
import csv
import math
import numpy as np
import os.path
import re


SIM_TYPE = 'webcon'

WANT_BROWSER_FRAME_CACHE = False

_SCHEMA = simulation_db.get_schema(SIM_TYPE)


def background_percent_complete(report, run_dir, is_running):
    if not is_running:
        data = None
        try:
            data = simulation_db.read_json(run_dir.join(template_common.INPUT_BASE_NAME))
        except IOError:
            pass
        return {
            'percentComplete': 100,
            'frameCount': 1,
            'columnInfo': _column_info(run_dir.join(_analysis_data_file(data))) if data else None,
        }
    return {
        'percentComplete': 0,
        'frameCount': 0,
    }


def fixup_old_data(data):
    for m in _SCHEMA.model:
        if m not in data.models:
            data.models[m] = pkcollections.Dict({})
        template_common.update_model_defaults(data.models[m], m, _SCHEMA)


def get_animation_name(data):
    return 'animation'


def get_data_file(run_dir, model, frame, options=None):
    assert False, 'not implemented'


def get_fit(data):
    fit_in = _analysis_data_file(data)
    col1 = int(data.models.fitReport.x)
    col2 = int(data.models.fitReport.y)

    x_vals, y_vals = np.loadtxt(fit_in, delimiter=',', skiprows=1, usecols=(col1, col2), unpack=True)
    col_info = _column_info(fit_in)

    fit_y, fit_y_min, fit_y_max, param_vals, latex_label = _fit_to_equation(
        x_vals,
        y_vals,
        data.models.fitter.equation,
        data.models.fitter.variable,
        data.models.fitter.parameters
    )
    data.models.fitReport.parameterValues = param_vals.tolist()


    plots = [
        {
            'points': (y_vals * col_info['scale'][1]).tolist(),
            'label': 'data',
            'style': 'scatter',
        },
        {
            'points': (fit_y * col_info['scale'][1]).tolist(),
            'label': 'fit',
        },
        {
            'points': (fit_y_min * col_info['scale'][1]).tolist(),
            'label': '',
            '_parent': 'fit'
        },
        {
            'points': (fit_y_max * col_info['scale'][1]).tolist(),
            'label': '',
            '_parent': 'fit'
        }
    ]

    return template_common.parameter_plot(x_vals.tolist(), plots, data, {
        'title': '',
        'y_label': _label(col_info, 1),
        'x_label': _label(col_info, 0),
        'p_vals': param_vals.tolist(),
        'latex_label': '$y = ' + latex_label + '$'
    })


def get_simulation_frame(run_dir, data, model_data):
    path = str(run_dir.join(_analysis_data_file(model_data)))
    plot_data = np.genfromtxt(path, delimiter=',', names=True)
    col_info = _column_info(path)
    report = template_common.parse_animation_args(
        data,
        {
            '': ['x', 'y1', 'y2', 'y3', 'startTime'],
        },
    )
    x_idx = _safe_index(plot_data, report.x)
    x = plot_data[plot_data.dtype.names[x_idx]].tolist()
    plots = []
    for f in ('y1', 'y2', 'y3'):
        if report[f] == 'none':
            continue
        idx = _safe_index(plot_data, report[f])
        col = plot_data.dtype.names[idx]
        if len(plot_data[col]) <= 0 or math.isnan(plot_data[col][0]):
            continue
        plots.append({
            'points': (plot_data[col] * col_info['scale'][idx]).tolist(),
            'label': _label(col_info, idx),
        })
    return template_common.parameter_plot(x, plots, data, {
        'title': '',
        'y_label': '',
        'x_label': _label(col_info, x_idx),
    })


def lib_files(data, source_lib):
    res = []
    if data.models.analysisData.file:
        res.append(_analysis_data_file(data))
    res = template_common.filename_to_path(res, source_lib)
    return res


def models_related_to_report(data):
    r = data['report']
    if r == get_animation_name(data):
        return []
    if r == 'fitReport':
        return [r, 'fitter']
    return [
        r,
    ]


def python_source_for_model(data, model):
    return _generate_parameters_file(data)


def validate_file(file_type, path):
    if not _column_info(path):
        return 'Invalid CSV header row'
    return None


def validate_sympy(str):
    try:
        sp.sympify(str)
        return True
    except:
        return False


def write_parameters(data, run_dir, is_parallel):
    pkio.write_text(
        run_dir.join(template_common.PARAMETERS_PYTHON_FILE),
        _generate_parameters_file(data),
    )


def _analysis_data_file(data):
    return template_common.lib_file_name('analysisData', 'file', data.models.analysisData.file)


def _column_info(path):
    # parse label/units from the csv header
    header = None
    with open(str(path)) as f:
        reader = csv.reader(f)
        for row in reader:
            header = row
            break
    if not header or not re.search(r'\w', header[0]) or len(header) < 2:
        return None
    res = {
        'names': [],
        'units': [],
        'scale': [],
    }
    for h in header:
        name = h
        units = ''
        scale = 1
        match = re.search(r'^(.*?)\s*(\(|\[)(.*?)(\)|\])\s*$', h)
        if match:
            name = match.group(1)
            units = match.group(3)
            #TODO(pjm): convert units to base for other cases
            match = re.search(r'^k(\w)', units)
            if match:
                units = match.group(1)
                scale = 1e3
        res['names'].append(name)
        res['units'].append(units)
        res['scale'].append(scale)
    return res


def _fit_to_equation(x, y, equation, var, params):

    # TODO: must sanitize input - sympy uses eval
    sym_curve = sp.sympify(equation)
    sym_str = var + ' ' + ' '.join(params)

    syms = sp.symbols(sym_str)
    sym_curve_l = sp.lambdify(syms, sym_curve, 'numpy')

    # feed a uniform x distribution to the function?  or sort?
    #x_uniform = np.linspace(np.min(x), np.max(x), 100)

    p_vals, pcov = curve_fit(sym_curve_l, x, y, maxfev=500000)
    sigma = np.sqrt(np.diagonal(pcov))

    p_subs = []
    p_subs_min = []
    p_subs_max = []
    p_rounded = []

    # exclude the symbol of the variable when subbing
    for sidx, p in enumerate(p_vals, 1):
        sig = sigma[sidx - 1]
        p_min = p - 2 * sig
        p_max = p + 2 * sig
        s = syms[sidx]
        p_subs.append((s, p))
        p_subs_min.append((s, p_min))
        p_subs_max.append((s, p_max))
        p_rounded.append((s, np.round(p, 3)))
    y_fit = sym_curve.subs(p_subs)
    y_fit_min = sym_curve.subs(p_subs_min)
    y_fit_max = sym_curve.subs(p_subs_max)

    # used for the laTeX label - rounding should take size of uncertainty into account
    y_fit_rounded = sym_curve.subs(p_rounded)

    y_fit_l = sp.lambdify(var, y_fit, 'numpy')
    y_fit_min_l = sp.lambdify(var, y_fit_min, 'numpy')
    y_fit_max_l = sp.lambdify(var, y_fit_max, 'numpy')

    return y_fit_l(x), y_fit_min_l(x), y_fit_max_l(x), p_vals, sp.latex(y_fit_rounded)


def _generate_parameters_file(data):
    return ''


def _label(col_info, idx):
    name = col_info['names'][idx]
    units = col_info['units'][idx]
    if units:
        return '{} [{}]'.format(name, units)
    return name


def _safe_index(values, idx):
    idx = int(idx)
    if idx >= len(values.dtype.names):
        idx = 1
    return idx
