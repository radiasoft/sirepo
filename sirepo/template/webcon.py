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

_BEAM_DATA_FILE = 'beam_data.npy'
_EXAMPLE_FOLDERS = pkcollections.Dict({
    'EPICS 00': '/Examples'
})
_SCHEMA = simulation_db.get_schema(SIM_TYPE)

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
    if 'folder' not in data['models']['simulation']:
        if data['models']['simulation']['name'] in _EXAMPLE_FOLDERS:
            data['models']['simulation']['folder'] = _EXAMPLE_FOLDERS[data['models']['simulation']['name']]
        else:
            data['models']['simulation']['folder'] = '/'

def get_data_file(run_dir, model, frame, options=None):
    f = run_dir.join(_BEAM_DATA_FILE)
    return f.basename, f.read(), 'text/csv'


def get_animation_name(data):
    return 'animation'


def get_data_file(run_dir, model, frame, options=None):
    assert False, 'not implemented'


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

# for validation of user input

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

def fit_to_function(data):

    # must sanitize input - sympy uses eval
    # 'a + b * x + c * x**2'
    # 'a * cos(b * x**2. + c) * exp(-x)'
    # 'a + b * sin(x + c)'
    eq_str = data.equation
    eq_ind_v = data.variable
    eq_fit_p = data.params

    xv = data.xVals
    yv = data.yVals

    sym_curve = sp.sympify(eq_str)
    sym_str = eq_ind_v
    for p in eq_fit_p:
        sym_str = sym_str + ' ' + p
    #pkdp(sym_str)

    syms = sp.symbols(sym_str)
    sym_curve_l = sp.lambdify(syms, sym_curve, 'numpy')

    p_vals, pcov = curve_fit(sym_curve_l, xv, yv, maxfev=500000)
    p_subs = []
    for sidx, p in enumerate(p_vals, 1):
        s = syms[sidx]
        #pkdp('{} subbing {}: {}', sidx, s, p)
        p_subs.append((s, p))
    y_fit = sym_curve.subs(p_subs)

    y_fit_l = sp.lambdify(eq_ind_v, y_fit, 'numpy')

    #pkdp('fitted {}', y_fit)
    #pkdp('best params:')
    #for pix, p in enumerate(eq_fit_p):
    #    pkdp('{}: {}', p, p_vals[pix])

    return {
        'xVals': xv,
        'yVals': y_fit_l(xv),
        'fits': p_vals
    }

def _extract_fit(run_dir, data, col1 = 0, col2 = 1):
    beam_data = np.loadtxt(str(run_dir.join(_BEAM_DATA_FILE)))
    if 'error' in beam_data:
        return beam_data

    beam_cols = np.transpose(beam_data)
    num_rows = len(beam_data)
    num_cols = len(beam_cols)
    assert col1 >= 0 and col1 < num_cols and col2 >= 0 and col2 < num_cols and col1 != col2

    data['xVals'] = beam_cols[col1]
    data['yVals'] = beam_cols[col2]
    fit = fit_to_function(data)

    return {
        'title': 'Best Fit',
        'xVals': fit.xVals,
        'yVals': fit.yVals,
        'fits': fit.fits
    }


def _safe_index(values, idx):
    idx = int(idx)
    if idx >= len(values.dtype.names):
        idx = 1
    return idx
