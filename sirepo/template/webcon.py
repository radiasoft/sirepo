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

_BEAM_DATA_FILE = 'beam_data.txt'
_EXAMPLE_FOLDERS = pkcollections.Dict({
    'EPICS 00': '/Examples'
})
_SCHEMA = simulation_db.get_schema(SIM_TYPE)

WANT_BROWSER_FRAME_CACHE = False

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
    if 'folder' not in data.models.simulation:
        if data.models.simulation.name in _EXAMPLE_FOLDERS:
            data.models.simulation.folder = _EXAMPLE_FOLDERS[data.models.simulation.name]
        else:
            data.models.simulation.folder = '/'


def get_data_file(run_dir, model, frame, options=None):
    f = run_dir.join(_BEAM_DATA_FILE)
    return f.basename, f.read(), 'text/csv'


def get_animation_name(data):
    return 'animation'


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
    return [
        r,
    ]


def python_source_for_model(data, model):
    return _generate_parameters_file(data)


def validate_file(file_type, path):
    if not _column_info(path):
        return 'Invalid CSV header row'
    return None


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


def _generate_parameters_file(data):
    return ''


def _label(col_info, idx):
    name = col_info['names'][idx]
    units = col_info['units'][idx]
    if units:
        return '{} [{}]'.format(name, units)
    return name


def validate_sympy(str):
    try:
        sp.sympify(str)
        return True
    except:
        return False


def fit_to_function(x, y, equation, var, params):

    # must sanitize input - sympy uses eval
    # 'a + b * x + c * x**2'
    # 'a * cos(b * x**2. + c) * exp(-x)'
    # 'a + b * sin(x + c)'
    #eq_str = data.models.fitter.equation
    #eq_ind_v = data.models.fitter.variable
    #eq_fit_p = data.models.fitter.params

    #xv = data.xVals
    #yv = data.yVals

    sym_curve = sp.sympify(equation)
    sym_str = var
    for p in params:
        sym_str = sym_str + ' ' + p
    #pkdp(sym_str)

    syms = sp.symbols(sym_str)
    sym_curve_l = sp.lambdify(syms, sym_curve, 'numpy')

    p_vals, pcov = curve_fit(sym_curve_l, x, y, maxfev=500000)
    p_subs = []
    for sidx, p in enumerate(p_vals, 1):
        s = syms[sidx]
        #pkdp('{} subbing {}: {}', sidx, s, p)
        p_subs.append((s, p))
    y_fit = sym_curve.subs(p_subs)

    y_fit_l = sp.lambdify(var, y_fit, 'numpy')

    #pkdp('fitted {}', y_fit)
    #pkdp('best params:')
    #for pix, p in enumerate(eq_fit_p):
    #    pkdp('{}: {}', p, p_vals[pix])

    return (y_fit_l(x), p_vals)
    #return {
    #    'xVals': xv,
    #    'yVals': y_fit_l(xv),
    #    'fits': p_vals
    #}

def extract_fit(data):
    fit_in = _analysis_data_file(data)
    col1 = int(data.models.fitReport.x)
    col2 = int(data.models.fitReport.y)
    #pkdp('!EXTRACT FIT col1 {} col2 {}', col1, col2)

    #pkdp('!EXTRACT FIT {} {}', data, fit_in)
    #beam_data = np.loadtxt(fit_in)
    x_vals, y_vals = np.loadtxt(fit_in, delimiter=',', skiprows=1, usecols=(col1, col2), unpack=True)
    #fit_cols = np.transpose(fit_data)
    #pkdp('!EXTRACT FIT FOR COLS {}', fit_cols)
    #num_rows = len(fit_data)
    #num_cols = len(fit_cols)
    #pkdp('!EXTRACT FIT FOR ROWS {} COLS {}', num_rows, num_cols)

    #x_vals = fit_cols[0]
    #y_vals = fit_cols[1]
    eq_str = data.models.fitter.equation
    eq_ind_v = data.models.fitter.variable
    eq_fit_p = data.models.fitter.parameters
    #pkdp('!EXTRACT FIT eq {} var {} params {}', eq_str, eq_ind_v, eq_fit_p)
    fit_y, param_vals = fit_to_function(x_vals, y_vals, eq_str, eq_ind_v, eq_fit_p)
    fit_data = np.transpose([x_vals, fit_y])
    fit_file = template_common.lib_file_name('analysisFit', 'file', data.models.analysisData.file)
    pkdp('!EXTRACT FIT param vals {} to file {}', param_vals, fit_file)
    np.savetxt(fit_file, fit_data, header='x,y', delimiter=',')

    return {
        'title': 'Best Fit',
        'fits': param_vals
    }
    #return {
    #    'title': 'Best Fit',
    ##    'xVals': fit.xVals,
    ##    'yVals': fit.yVals,
     #   'fits': fit.fits
    #}


def _safe_index(values, idx):
    idx = int(idx)
    if idx >= len(values.dtype.names):
        idx = 1
    return idx
