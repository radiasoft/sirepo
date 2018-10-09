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
    ]:
        if m not in data['models']:
            data['models'][m] = {}
        template_common.update_model_defaults(data['models'][m], m, _SCHEMA)


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
    frame_index = int(data['frameIndex'])
    report = template_common.parse_animation_args(
        data,
        {'': ['x', 'y', 'histogramBins', 'startTime']},
    )
    from zgoubi import core, io
    data = io.read_file(str(run_dir.join(_ZGOUBI_DATA_FILE)))
    x_info = _FIELD_INFO[report['x']]
    x = []
    y_info = _FIELD_INFO[report['y']]
    y = []
    for row in data:
        x.append(row[x_info[0]])
        y.append(row[y_info[0]])
    x = np.array(x) * x_info[2]
    y = np.array(y) * y_info[2]
    hist, edges = np.histogramdd([x, y], template_common.histogram_bins(report.histogramBins))
    return {
        'x_range': [float(edges[0][0]), float(edges[0][-1]), len(hist)],
        'y_range': [float(edges[1][0]), float(edges[1][-1]), len(hist[0])],
        'x_label': x_info[1],
        'y_label': y_info[1],
        'title': '',
        'z_matrix': hist.T.tolist(),
        'z_label': 'Number of Particles',
    }


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


def _generate_beamline(data, beamline_map, element_map, beamline_id):
    res = ''
    #pkdp('beamline: {}', beamline_map[beamline_id]['items'])
    for item_id in beamline_map[beamline_id]['items']:
        if item_id in beamline_map:
            res += _generate_beamline(data, beamline_map, element_map, item_id)
            continue
        el = element_map[item_id]
        if el['type'] == 'CHANGREF':
            res += 'line.add(core.{}(ALE={}, XCE={}, YCE={}))\n'.format(el.type, _degrees(el.angle), _cm(el.xce), _cm(el.yce))
        elif el['type'] == 'DRIFT':
            res += 'line.add(core.{}("{}", XL={}))\n'.format(el.type, el.name, _cm(el.l))
        elif el['type'] == 'MARKER':
            res += 'line.add(core.{}("{}", label2="{}"))\n'.format(el.type, el.name, '.plt' if int(el.plt) else '')
        elif el['type'] == 'QUADRUPO':
            res += 'line.add(core.{}("{}", XL={}, R_0={}, B_0={}, XPAS={}, KPOS={}))\n'.format(el.type, el.name, _cm(el.l), _cm(el.r_0), el.b_0, _cm(el.xpas), el.kpos)
        elif el['type'] == 'BEND':
            res += 'line.add(core.{}("{}", XL={}, B1={}, KPOS=3, ALE={}))\n'.format(el.type, el.name, _cm(el.l), el.b1, _degrees(el.angle))
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
    #pkdp('target beamline: {}', sim['visualizationBeamlineId'])
    return _generate_beamline(data, beamline_map, element_map, sim['visualizationBeamlineId'])


def _generate_parameters_file(data):
    v = template_common.flatten_data(data['models'], {})
    v['beamlineElements'] = _generate_beamline_elements(data)
    return template_common.render_jinja(SIM_TYPE, v)
