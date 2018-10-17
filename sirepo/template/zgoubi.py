# -*- coding: utf-8 -*-
u"""zgoubi execution template.

:copyright: Copyright (c) 2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkcollections
from pykern import pkio
from pykern import pkjinja
from pykern.pkdebug import pkdc, pkdp
from sirepo import simulation_db
from sirepo.template import template_common
import math
import numpy as np
import re

SIM_TYPE = 'zgoubi'

WANT_BROWSER_FRAME_CACHE = False

ZGOUBI_LOG_FILE = 'sr_zgoubi.log'

_ZGOUBI_DATA_FILE = 'zgoubi.fai'

_SCHEMA = simulation_db.get_schema(SIM_TYPE)


def background_percent_complete(report, run_dir, is_running):
    data_file = run_dir.join(_ZGOUBI_DATA_FILE)
    if not is_running and data_file.exists():
        return {
            'percentComplete': 100,
            'frameCount': 1,
        }
    return {
        'percentComplete': 0,
        'frameCount': 0,
    }


def fixup_old_data(data):
    for m in [
            'bunchAnimation',
            'simulationSettings',
            'opticsAnimation',
    ]:
        if m not in data['models']:
            data['models'][m] = {}
        template_common.update_model_defaults(data['models'][m], m, _SCHEMA)
    for el in data['models']['elements']:
        template_common.update_model_defaults(el, el['type'], _SCHEMA)


def get_animation_name(data):
    return 'animation'


_FIELD_INFO = {
    'Do1': [1, u'dp/p₀', 1],
    'Yo': [2, u'Y₀ [m]', 0.01],
    'To': [3, u'Y\'₀ [rad]', 0.001],
    'Zo': [4, u'Z₀ [m]', 0.01],
    'Po': [5, u'Z\'₀ [rad]', 0.001],
    'So': [6, u's₀ [m]', 0.01],
    'to': [7, u't₀', 1],
    'D1': [8, 'dp/p', 1],
    'Y': [9, 'Y [m]', 0.01],
    'T': [10, 'Y\' [rad]', 0.001],
    'Z': [11, 'Z [m]', 0.01],
    'P': [12, 'Z\' [rad]', 0.001],
    'S': [13, 's [m]', 0.01],
    'time': [14, 't', 1],
}

# KEX, Do-1, Yo, To, Zo, Po, So, to, D-1, Y, T, Z, P, S, time, SXo, SYo, SZo, modSo, SX, SY, SZ, modS, ENEKI, ENERG, IT, IREP, SORT, M, Q, G, tau, unused, RET, DPR, PS, BORO, IPASS, NOEL, KLEY, LABEL1, LABEL2, LET
# int, float, cm, mrd, cm, mrd, cm, mu_s, float, cm, mrd, cm, mrd, cm, mu_s, float,float,float, float, float,float,float,float,     MeV,   MeV, int,  int,   cm, MeV/c2, C, float, float,  float, float, float, float, kG.cm,   int,  int, string,  string, string, string

def get_simulation_frame(run_dir, data, model_data):
    if data['modelName'] == 'bunchAnimation':
        return _extract_bunch_animation(run_dir, data, model_data)
    if data['modelName'] == 'opticsAnimation':
        return _extract_optics_animation(run_dir, data, model_data)
    assert False, 'invalid animation frame model: {}'.format(data['modelName'])


def lib_files(data, source_lib):
    return []


def models_related_to_report(data):
    r = data['report']
    if r == get_animation_name(data):
        return []
    return [
        r
    ]


def python_source_for_model(data, model):
    return _generate_parameters_file(data)


def write_parameters(data, run_dir, is_parallel):
    pkio.write_text(
        run_dir.join(template_common.PARAMETERS_PYTHON_FILE),
        _generate_parameters_file(data),
    )


_FIELD_MAP = {
    'l': 'xl',
    'angle': 'ale',
}


#TODO(pjm): see template/shadow.py for an example of converting all fields to cm
def _cm(meters):
    return meters * 100


def _degrees(radians):
    return float(radians) * 180 / math.pi


def _extract_bunch_animation(run_dir, data, model_data):
    report = template_common.parse_animation_args(
        data,
        {'': ['x', 'y', 'histogramBins', 'startTime']},
    )
    x_info = _FIELD_INFO[report['x']]
    y_info = _FIELD_INFO[report['y']]
    col_names, rows = _read_data_file(run_dir.join(_ZGOUBI_DATA_FILE))
    x = np.array(_column_data(report['x'], col_names, rows)) * x_info[2]
    y = np.array(_column_data(report['y'], col_names, rows)) * y_info[2]
    hist, edges = np.histogramdd([x, y], template_common.histogram_bins(report.histogramBins), range=[[-0.4, 0.15], [-0.2, 0.2]])
    return {
        'x_range': [float(edges[0][0]), float(edges[0][-1]), len(hist)],
        'y_range': [float(edges[1][0]), float(edges[1][-1]), len(hist[0])],
        'x_label': x_info[1],
        'y_label': y_info[1],
        'title': '',
        'z_matrix': hist.T.tolist(),
        'z_label': 'Number of Particles',
    }


def _column_data(col, col_names, rows):
    idx = col_names.index(col)
    assert idx >= 0, 'invalid col: {}'.format(col)
    res = []
    for row in rows:
        res.append(float(row[idx]))
    return res


def _extract_optics_animation(run_dir, data, model_data):
    report = template_common.parse_animation_args(
        data,
        {'': ['y1', 'y2', 'y3', 'startTime']},
    )
    col_names, rows = _read_data_file(run_dir.join('zgoubi.OPTICS.out'))
    plots = []
    for f in ('y1', 'y2', 'y3'):
        if report[f] == 'none':
            continue
        plots.append({
            'points': _column_data(report[f], col_names, rows),
            'label': template_common.enum_text(_SCHEMA, 'OpticsParameter', report[f]),
        })
    x = _column_data('cumulsm', col_names, rows)
    return {
        'title': '',
        'x_range': [min(x), max(x)],
        'y_label': '',
        'x_label': 's [m]',
        'x_points': x,
        'plots': plots,
        'y_range': template_common.compute_plot_color_and_range(plots),
    }


def _generate_beamline(data, beamline_map, element_map, beamline_id):
    res = ''
    for item_id in beamline_map[beamline_id]['items']:
        if item_id in beamline_map:
            res += _generate_beamline(data, beamline_map, element_map, item_id)
            continue
        el = element_map[item_id]
        if el['type'] == 'AUTOREF':
            res += 'line.add(core.FAKE_ELEM(""" \'AUTOREF\'\n{}\n{} {} {}\n"""))\n'.format(el.I, _cm(el.XCE), _cm(el.YCE), _mrad(el.ALE))
        elif el['type'] == 'BEND':
            res += 'line.add(core.{}("{}", XL={}, B1={}, KPOS=3, ALE={}))\n'.format(el.type, el.name, _cm(el.XL), el.B1, _degrees(el.ALE))
        elif el['type'] == 'CHANGREF':
            res += 'line.add(core.{}(ALE={}, XCE={}, YCE={}))\n'.format(el.type, _degrees(el.ALE), _cm(el.XCE), _cm(el.YCE))
        elif el['type'] == 'DRIFT':
            res += 'line.add(core.{}("{}", XL={}))\n'.format(el.type, el.name, _cm(el.XL))
        elif el['type'] == 'MARKER':
            res += 'line.add(core.{}("{}", label2="{}"))\n'.format(el.type, el.name, '.plt' if int(el.plt) else '')
        elif el['type'] == 'MULTIPOL':
            res += 'line.add(core.{}("{}", XL={}, R_0={}, B_1={}, B_2={}, B_3={}, B_4={}, B_5={}, B_6={}, B_7={}, B_8={}, B_9={}, B_10={}, X_E={}, LAM_E={}, E_2={}, E_3={}, E_4={}, E_5={}, E_6={}, E_7={}, E_8={}, E_9={}, E_10={}, C_0={}, C_1={}, C_2={}, C_3={}, C_4={}, C_5={}, X_S={}, LAM_S={}, S_2={}, S_3={}, S_4={}, S_5={}, S_6={}, S_7={}, S_8={}, S_9={}, S_10={}, CS_0={}, CS_1={}, CS_2={}, CS_3={}, CS_4={}, CS_5={}, R_1={}, R_2={}, R_3={}, R_4={}, R_5={}, R_6={}, R_7={}, R_8={}, R_9={}, R_10={}, XPAS={}, KPOS={}, XCE={}, YCE={}, ALE={}))\n'.format(el.type, el.name, _cm(el.XL), _cm(el.R_0), el.B_1, el.B_2, el.B_3, el.B_4, el.B_5, el.B_6, el.B_7, el.B_8, el.B_9, el.B_10, _cm(el.X_E), _cm(el.LAM_E), el.E_2, el.E_3, el.E_4, el.E_5, el.E_6, el.E_7, el.E_8, el.E_9, el.E_10, el.C_0, el.C_1, el.C_2, el.C_3, el.C_4, el.C_5, _cm(el.X_S), _cm(el.LAM_S), el.S_2, el.S_3, el.S_4, el.S_5, el.S_6, el.S_7, el.S_8, el.S_9, el.S_10, el.CS_0, el.CS_1, el.CS_2, el.CS_3, el.CS_4, el.CS_5, el.R_1, el.R_2, el.R_3, el.R_4, el.R_5, el.R_6, el.R_7, el.R_8, el.R_9, el.R_10, _xpas(el.XPAS), el.KPOS, _cm(el.XCE), _cm(el.YCE), el.ALE)
        elif el['type'] == 'QUADRUPO':
            res += 'line.add(core.{}("{}", XL={}, R_0={}, B_0={}, XPAS={}, KPOS={}))\n'.format(el.type, el.name, _cm(el.XL), _cm(el.R_0), el.B_0, _cm(float(el.XPAS)), el.KPOS)
        elif el['type'] == 'YMY':
            res += 'line.add(core.FAKE_ELEM(""" \'YMY\'\n"""))\n'
    return res


def _generate_beamline_elements(data):
    res = ''
    sim = data['models']['simulation']
    beamline_map = {}
    for bl in data.models.beamlines:
        beamline_map[bl.id] = bl
    element_map = {}
    for el in data.models.elements:
        element_map[el._id] = el
    if 'visualizationBeamlineId' not in sim or not sim['visualizationBeamlineId']:
        sim['visualizationBeamlineId'] = data.models.beamlines[0].id
    return _generate_beamline(data, beamline_map, element_map, sim['visualizationBeamlineId'])


def _generate_parameters_file(data):
    v = template_common.flatten_data(data['models'], {})
    v['beamlineElements'] = _generate_beamline_elements(data)
    return template_common.render_jinja(SIM_TYPE, v)


def _mrad(mrad):
    return float(mrad) * 1000


def _read_data_file(path):
    text = pkio.read_text(path)
    # mode: title -> header -> data
    mode = 'title'
    col_names = []
    rows = []
    for line in text.split("\n"):
        if mode == 'title':
            mode = 'header'
            continue
        if mode == 'header':
            # header row starts with '# <letter>'
            if re.search('^#\s+[a-zA-Z]', line):
                col_names = re.split('\s+', line)
                col_names = map(lambda x: re.sub(r'\W|_', '', x), col_names[1:])
                mode = 'data'
        elif mode == 'data':
            if re.search('^#', line):
                continue
            row = re.split('\s+', re.sub(r'^\s+', '', line))
            rows.append(row)
    rows.pop()
    return col_names, rows

def _xpas(v):
    if re.search(r'^#', v):
        v = re.sub(r'^#', '', v)
        return '[{}]'.format(','.join(v.split('|')))
    return float(v)
