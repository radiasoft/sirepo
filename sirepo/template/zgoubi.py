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
import py.path
import re

SIM_TYPE = 'zgoubi'

BUNCH_SUMMARY_FILE = 'bunch.json'

WANT_BROWSER_FRAME_CACHE = True

ZGOUBI_LOG_FILE = 'sr_zgoubi.log'

_SCHEMA = simulation_db.get_schema(SIM_TYPE)

_ZGOUBI_DATA_FILE = 'zgoubi.fai'

_ZGOUBI_LOG_FILE = 'zgoubi.res'

_INITIAL_PHASE_MAP = {
    'D1': 'Do1',
    'time': 'to',
}

_MODEL_UNITS = None

_PHASE_SPACE_FIELD_INFO = {
    'Do1': [u'dp/p₀', 1],
    'Yo': [u'Y₀ [m]', 0.01],
    'To': [u'Y\'₀ [rad]', 0.001],
    'Zo': [u'Z₀ [m]', 0.01],
    'Po': [u'Z\'₀ [rad]', 0.001],
    'So': [u's₀ [m]', 0.01],
    'to': [u't₀', 1],
    'D1': ['dp/p', 1],
    'Y': ['Y [m]', 0.01],
    'T': ['Y\' [rad]', 0.001],
    'Z': ['Z [m]', 0.01],
    'P': ['Z\' [rad]', 0.001],
    'S': ['s [m]', 0.01],
    'time': ['t', 1],
}

_PYZGOUBI_FIELD_MAP = {
    'l': 'XL',
    'angle': 'ALE',
    'plt': 'label2',
}

_REPORT_INFO = {
    'twissReport': ['zgoubi.TWISS.out', 'TwissParameter', 'sums'],
    'twissReport2': ['zgoubi.TWISS.out', 'TwissParameter', 'sums'],
    'opticsReport': ['zgoubi.OPTICS.out', 'OpticsParameter', 'cumulsm'],
}


def background_percent_complete(report, run_dir, is_running):
    errors = ''
    if not is_running:
        data_file = run_dir.join(_ZGOUBI_DATA_FILE)
        if data_file.exists():
            col_names, rows = read_data_file(data_file)
            count = int(rows[-1][col_names.index('IPASS')])
            return {
                'percentComplete': 100,
                'frameCount': count + 1,
            }
        else:
            errors = _parse_zgoubi_log(run_dir)
    return {
        'percentComplete': 0,
        'frameCount': 0,
        'error': errors,
    }


def column_data(col, col_names, rows):
    idx = col_names.index(col)
    assert idx >= 0, 'invalid col: {}'.format(col)
    res = []
    for row in rows:
        res.append(float(row[idx]))
    return res


def extract_first_twiss_row(run_dir):
    filename = _REPORT_INFO['twissReport'][0]
    col_names, rows = read_data_file(py.path.local(run_dir).join(filename))
    return col_names, rows[0]


def fixup_old_data(data):
    #TODO(pjm): remove all fixups when merged with master
    for m in [
            'bunch',
            'bunchAnimation',
            'bunchAnimation2',
            'simulationSettings',
            'opticsReport',
            'twissReport',
            'twissReport2',
    ]:
        if m not in data.models:
            data.models[m] = pkcollections.Dict({})
        template_common.update_model_defaults(data.models[m], m, _SCHEMA)
    if 'beamParameters' in data.models:
        data.models.bunch['particleType'] = data.models.beamParameters.particleType
        data.models.bunch.rigidity = data.models.beamParameters.rigidity
        del data.models['beamParameters']
    for el in data.models.elements:
        template_common.update_model_defaults(el, el['type'], _SCHEMA)
    if 'bunchReport1' not in data['models']:
        for i in range(4):
            m = 'bunchReport{}'.format(i + 1)
            model = data['models'][m] = {}
            template_common.update_model_defaults(data['models'][m], 'bunchReport', _SCHEMA)
            if i == 0:
                model['y'] = 'T'
            elif i == 1:
                model['x'] = 'Z'
                model['y'] = 'P'
            elif i == 3:
                model['x'] = 'S'
                model['y'] = 'time'


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
    res = ['bunch']
    if 'bunchReport' in r:
        if data.models.bunch.match_twiss_parameters == '1':
            res.append('simulation.visualizationBeamlineId')
    res += [
        'beamlines',
        'elements',
    ]
    if r == 'twissReport':
        res.append('simulation.activeBeamlineId')
    if r == 'twissReport2' or 'opticsReport' in r:
        res.append('simulation.visualizationBeamlineId')
    return res


def parse_error_log(run_dir):
    return None


def python_source_for_model(data, model):
    return _generate_parameters_file(data)


def prepare_output_file(report_info, data):
    report = data['report']
    if 'bunchReport' in report or 'twissReport' in report or 'opticsReport' in report:
        fn = simulation_db.json_filename(template_common.OUTPUT_BASE_NAME, report_info.run_dir)
        if fn.exists():
            fn.remove()
            save_report_data(data, report_info.run_dir)


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


def remove_last_frame(run_dir):
    pass


def save_report_data(data, run_dir):
    report_name = data['report']
    if 'twissReport' in report_name or 'opticsReport' in report_name:
        filename, enum_name, x_field = _REPORT_INFO[report_name]
        report = data['models'][report_name]
        plots = []
        col_names, rows = read_data_file(py.path.local(run_dir).join(filename))
        for f in ('y1', 'y2', 'y3'):
            if report[f] == 'none':
                continue
            plots.append({
                'points': column_data(report[f], col_names, rows),
                'label': template_common.enum_text(_SCHEMA, enum_name, report[f]),
            })
        x = column_data(x_field, col_names, rows)
        res = {
            'title': '',
            'x_range': [min(x), max(x)],
            'y_label': '',
            'x_label': 's [m]',
            'x_points': x,
            'plots': plots,
            'y_range': template_common.compute_plot_color_and_range(plots),
        }
    elif 'bunchReport' in report_name:
        report = data['models'][report_name]
        col_names, rows = read_data_file(py.path.local(run_dir).join(_ZGOUBI_DATA_FILE))
        res = _extract_bunch_data(report, col_names, rows, '')
        summary_file = py.path.local(run_dir).join(BUNCH_SUMMARY_FILE)
        if summary_file.exists():
            res['summaryData'] = {
                'bunch': simulation_db.read_json(summary_file)
            }
    else:
        raise RuntimeError('unknown report: {}'.format(report_name))
    simulation_db.write_result(
        res,
        run_dir=run_dir,
    )


def simulation_dir_name(report_name):
    if 'bunchReport' in report_name:
        return 'bunchReport'
    return report_name


def write_parameters(data, run_dir, is_parallel, python_file=template_common.PARAMETERS_PYTHON_FILE):
    pkio.write_text(
        run_dir.join(python_file),
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
    col_names, all_rows = read_data_file(run_dir.join(_ZGOUBI_DATA_FILE))
    rows = []
    ipass_index = int(col_names.index('IPASS'))
    for row in all_rows:
        if int(row[ipass_index]) == frame_index:
            rows.append(row)
    return _extract_bunch_data(report, col_names, rows, 'Initial Distribution' if is_frame_0 else 'Pass {}'.format(frame_index))


def _extract_bunch_data(report, col_names, rows, title):
    x_info = _PHASE_SPACE_FIELD_INFO[report['x']]
    y_info = _PHASE_SPACE_FIELD_INFO[report['y']]
    x = np.array(column_data(report['x'], col_names, rows)) * x_info[1]
    y = np.array(column_data(report['y'], col_names, rows)) * y_info[1]
    hist, edges = np.histogramdd([x, y], template_common.histogram_bins(report.histogramBins))
    return {
        'x_range': [float(edges[0][0]), float(edges[0][-1]), len(hist)],
        'y_range': [float(edges[1][0]), float(edges[1][-1]), len(hist[0])],
        'x_label': x_info[0],
        'y_label': y_info[0],
        'title': title,
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
    if 'twissReport' in report:
        return template_common.render_jinja(SIM_TYPE, v, 'twiss.py')
    if 'opticsReport' in report:
        return template_common.render_jinja(SIM_TYPE, v, 'optics.py')
    v['outputFile'] = _ZGOUBI_DATA_FILE
    res = template_common.render_jinja(SIM_TYPE, v, 'bunch.py')
    if 'bunchReport' in report:
        return res + template_common.render_jinja(SIM_TYPE, v, 'bunch-report.py')
    return res + template_common.render_jinja(SIM_TYPE, v)


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

def _parse_zgoubi_log(run_dir):
    path = run_dir.join(_ZGOUBI_LOG_FILE)
    if not path.exists():
        return ''
    res = ''
    element_by_num = {}
    text = pkio.read_text(str(path))

    for line in text.split("\n"):
        match = re.search(r'^ (\'\w+\'.*?)\s+(\d+)$', line)
        if match:
            element_by_num[match.group(2)] = match.group(1)
            continue
        if re.search('all particles lost', line):
            res += '{}\n'.format(line)
            continue
        match = re.search(r'Enjob occured at element # (\d+)', line)
        if match:
            res += '{}\n'.format(line)
            num = match.group(1)
            if num in element_by_num:
                res += '  element # {}: {}\n'.format(num, element_by_num[num])
    return res



_MODEL_UNITS = _init_model_units()
