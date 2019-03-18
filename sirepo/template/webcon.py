# -*- coding: utf-8 -*-
u"""Webcon execution template.

:copyright: Copyright (c) 2017-2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkcollections
from pykern import pkio
from pykern import pkjinja
from pykern.pkdebug import pkdc, pkdp
from scipy.optimize import curve_fit
from sirepo import simulation_db
from sirepo.template import template_common
import copy
import sympy as sp
import numpy as np


SIM_TYPE = 'webcon'

_BEAM_DATA_FILE = 'beam_data.npy'
_EXAMPLE_FOLDERS = pkcollections.Dict({
    'EPICS 00': '/Examples'
})
_SCHEMA = simulation_db.get_schema(SIM_TYPE)


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


def lib_files(data, source_lib):
    return []


def models_related_to_report(data):
    r = data['report']
    return [r]


def python_source_for_model(data, model):
    return _generate_parameters_file(data)


def write_parameters(data, run_dir, is_parallel):
    pkio.write_text(
        run_dir.join(template_common.PARAMETERS_PYTHON_FILE),
        _generate_parameters_file(data),
    )


# for validation of user input
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

def _generate_parameters_file(data):
    pass
