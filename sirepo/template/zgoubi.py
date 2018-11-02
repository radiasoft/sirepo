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

WANT_BROWSER_FRAME_CACHE = True

ZGOUBI_LOG_FILE = 'sr_zgoubi.log'

_REPORT_STYLE_FIELDS = ['colorMap', 'includeLattice', 'notes']
_SCHEMA = simulation_db.get_schema(SIM_TYPE)
_ZGOUBI_DATA_FILE = 'zgoubi.fai'

_INITIAL_PHASE_MAP = {
    'D1': 'Do1',
    'time': 'to',
}

_MODEL_UNITS = None

_PHASE_SPACE_FIELD_INFO = {
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

_PYZGOUBI_FIELD_MAP = {
    'l': 'XL',
    'angle': 'ALE',
    'plt': 'label2',
}


def background_percent_complete(report, run_dir, is_running):
    data_file = run_dir.join(_ZGOUBI_DATA_FILE)
    if not is_running and data_file.exists():
        col_names, rows = read_data_file(data_file)
        count = int(rows[-1][col_names.index('IPASS')])
        return {
            'percentComplete': 100,
            'frameCount': count + 1,
        }
    return {
        'percentComplete': 0,
        'frameCount': 0,
    }


def column_data(col, col_names, rows):
    idx = col_names.index(col)
    assert idx >= 0, 'invalid col: {}'.format(col)
    res = []
    for row in rows:
        res.append(float(row[idx]))
    return res


def fixup_old_data(data):
    for m in [
            'beamParameters',
            'bunchAnimation',
            'bunchAnimation2',
            'simulationSettings',
            'opticsReport',
            'twissReport',
    ]:
        if m not in data['models']:
            data['models'][m] = {}
        template_common.update_model_defaults(data['models'][m], m, _SCHEMA)
    for el in data['models']['elements']:
        template_common.update_model_defaults(el, el['type'], _SCHEMA)


def get_animation_name(data):
    return 'animation'


def get_simulation_frame(run_dir, data, model_data):
    if re.search(r'bunchAnimation', data['modelName']):
        return _extract_bunch_animation(run_dir, data, model_data)
    assert False, 'invalid animation frame model: {}'.format(data['modelName'])


def lib_files(data, source_lib):
    return []


def models_related_to_report(data):
    r = data['report']
    if r == get_animation_name(data):
        return []
    res = template_common.report_fields(data, r, _REPORT_STYLE_FIELDS) + [
        'beamParameters',
        'beamlines',
        'elements',
    ]
    if r == 'twissReport':
        res.append('simulation.activeBeamlineId')
    if r == 'opticsReport':
        res.append('simulation.visualizationBeamlineId')
    return res


def parse_error_log(run_dir):
    return None


def python_source_for_model(data, model):
    return _generate_parameters_file(data)


def read_data_file(path):
    text = pkio.read_text(path)
    # mode: title -> header -> data
    mode = 'title'
    col_names = []
    rows = []
    for line in text.split("\n"):
        if mode == 'title':
            if not re.search(r'^\@', line):
                mode = 'header'
            continue
        if mode == 'header':
            # header row starts with '# <letter>'
            if re.search(r'^#\s+[a-zA-Z]', line):
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


def write_parameters(data, run_dir, is_parallel):
    pkio.write_text(
        run_dir.join(template_common.PARAMETERS_PYTHON_FILE),
        _generate_parameters_file(data),
    )


def _element_value(el, field):
    converter = _MODEL_UNITS.get(el['type'], {}).get(field, None)
    return converter(el[field]) if converter else el[field]


def _extract_bunch_animation(run_dir, data, model_data):
    # KEX, Do-1, Yo, To, Zo, Po, So, to, D-1, Y, T, Z, P, S, time, SXo, SYo, SZo, modSo, SX, SY, SZ, modS, ENEKI, ENERG, IT, IREP, SORT, M, Q, G, tau, unused, RET, DPR, PS, BORO, IPASS, NOEL, KLEY, LABEL1, LABEL2, LET
    # int, float, cm, mrd, cm, mrd, cm, mu_s, float, cm, mrd, cm, mrd, cm, mu_s, float,float,float, float, float,float,float,float,     MeV,   MeV, int,  int,   cm, MeV/c2, C, float, float,  float, float, float, float, kG.cm,   int,  int, string,  string, string, string
    #TODO(pjm): extract units from datafile
    frame_index = int(data['frameIndex'])
    report = template_common.parse_animation_args(
        data,
        {'': ['x', 'y', 'histogramBins', 'startTime']},
    )
    is_frame_0 = False
    # remap frame 0 to use initial "o" values from frame 1
    if frame_index == 0:
        is_frame_0 = True
        for f in ('x', 'y'):
            v = report[f]
            report[f] = _INITIAL_PHASE_MAP.get(v, '{}o'.format(v))
        frame_index = 1
    x_info = _PHASE_SPACE_FIELD_INFO[report['x']]
    y_info = _PHASE_SPACE_FIELD_INFO[report['y']]
    col_names, all_rows = read_data_file(run_dir.join(_ZGOUBI_DATA_FILE))
    rows = []
    ipass_index = int(col_names.index('IPASS'))
    for row in all_rows:
        if int(row[ipass_index]) == frame_index:
            rows.append(row)
    x = np.array(column_data(report['x'], col_names, rows)) * x_info[2]
    y = np.array(column_data(report['y'], col_names, rows)) * y_info[2]
    hist, edges = np.histogramdd([x, y], template_common.histogram_bins(report.histogramBins))#, range=[[-0.4, 0.3], [-0.2, 0.1]])
    return {
        'x_range': [float(edges[0][0]), float(edges[0][-1]), len(hist)],
        'y_range': [float(edges[1][0]), float(edges[1][-1]), len(hist[0])],
        'x_label': x_info[1],
        'y_label': y_info[1],
        'title': 'Initial Distribution' if is_frame_0 else 'Pass {}'.format(frame_index),
        'z_matrix': hist.T.tolist(),
        'z_label': 'Number of Particles',
    }


def _generate_beamline(data, beamline_map, element_map, beamline_id):
    res = ''
    for item_id in beamline_map[beamline_id]['items']:
        if item_id in beamline_map:
            res += _generate_beamline(data, beamline_map, element_map, item_id)
            continue
        el = element_map[item_id]
        if el['type'] == 'AUTOREF':
            res += 'line.add(core.FAKE_ELEM(""" \'AUTOREF\'\n{}\n{} {} {}\n"""))\n'.format(
                el.I, _element_value(el, 'XCE'), _element_value(el, 'YCE'), _element_value(el, 'angle'))
        elif el['type'] == 'YMY':
            res += 'line.add(core.FAKE_ELEM(""" \'YMY\'\n"""))\n'
        else:
            assert el['type'] in _MODEL_UNITS, 'Unsupported element: {}'.format(el['type'])
            res += _generate_element(el)
    return res


def _generate_beamline_elements(report, data):
    res = ''
    sim = data['models']['simulation']
    beamline_map = {}
    for bl in data.models.beamlines:
        beamline_map[bl.id] = bl
    element_map = {}
    for el in data.models.elements:
        element_map[el._id] = el
    if report == 'twissReport':
        beamline_id = sim['activeBeamlineId']
    else:
        if 'visualizationBeamlineId' not in sim or not sim['visualizationBeamlineId']:
            sim['visualizationBeamlineId'] = data.models.beamlines[0].id
        beamline_id = sim['visualizationBeamlineId']
    return _generate_beamline(data, beamline_map, element_map, beamline_id)


def _generate_element(el):
    res = 'line.add(core.{}("{}"'.format(el.type, el.name)
    for f in _SCHEMA.model[el.type]:
        if f == 'name' or f == 'order' or f == 'format':
            continue
        res += ', {}={}'.format(_PYZGOUBI_FIELD_MAP.get(f, f), _element_value(el, f))
    res += '))\n'
    return res


def _generate_parameters_file(data):
    v = template_common.flatten_data(data['models'], {})
    report = data['report'] if 'report' in data else ''
    v['beamlineElements'] = _generate_beamline_elements(report, data)
    if report == 'twissReport':
        return template_common.render_jinja(SIM_TYPE, v, 'twiss.py')
    if report == 'opticsReport':
        return template_common.render_jinja(SIM_TYPE, v, 'optics.py')
    v['outputFile'] = _ZGOUBI_DATA_FILE
    return template_common.render_jinja(SIM_TYPE, v)


def _init_model_units():
    # Convert element units (m, rad) to the required zgoubi units (cm, mrad, degrees)

    def _cm(meters):
        return float(meters) * 100

    def _degrees(radians):
        return float(radians) * 180 / math.pi

    def _marker_plot(v):
        return '"{}"'.format('.plt' if int(v) else '')

    def _mrad(mrad):
        return float(mrad) * 1000

    def _xpas(v):
        if re.search(r'^#', v):
            v = re.sub(r'^#', '', v)
            return '[{}]'.format(','.join(v.split('|')))
        return float(v)

    return {
        'AUTOREF': {
            'XCE': _cm,
            'YCE': _cm,
            'angle': _mrad,
        },
        'BEND': {
            'l': _cm,
            'XCE': _cm,
            'YCE': _cm,
        },
        'CHANGREF': {
            'angle': _degrees,
            'XCE': _cm,
            'YCE': _cm,
        },
        'DRIFT': {
            'l': _cm,
        },
        'MARKER': {
            'plt': _marker_plot,
        },
        'MULTIPOL': {
            'l': _cm,
            'R_0': _cm,
            'X_E': _cm,
            'LAM_E': _cm,
            'X_S': _cm,
            'LAM_S': _cm,
            'XPAS': _xpas,
            'XCE': _cm,
            'YCE': _cm,
        },
        'QUADRUPO': {
            'l': _cm,
            'R_0': _cm,
            'X_E': _cm,
            'LAM_E': _cm,
            'X_S': _cm,
            'LAM_S': _cm,
            'XCE': _cm,
            'YCE': _cm,
        },
    }

_MODEL_UNITS = _init_model_units()
