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
import io
import locale
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

_ZGOUBI_TWISS_FILE = 'zgoubi.TWISS.out'

_INITIAL_PHASE_MAP = {
    'D1': 'Do1',
    'time': 'to',
}

_MODEL_UNITS = None

_ANIMATION_FIELD_INFO = {
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
    'time': ['t [s]', 1],
    'RET': ['RF Phase [rad]', 1],
    'DPR': ['dp/p', 1e6],
    'ENEKI': ['Kenetic Energy [eV]', 1e6],
    'ENERG': ['Energy [eV]', 1e6],
    'IPASS': ['Turn Number', 1],
    'SX': ['Spin X', 1],
    'SY': ['Spin Y', 1],
    'SZ': ['Spin Z', 1],
}

_PYZGOUBI_FIELD_MAP = {
    'l': 'XL',
    'plt': 'label2',
}

_REPORT_ENUM_INFO = {
    'twissReport': 'TwissParameter',
    'twissReport2': 'TwissParameter',
    'opticsReport': 'OpticsParameter',
}

_TWISS_SUMMARY_LABELS = {
    'LENGTH': 'Beamline length [m]',
    'ORBIT5': 'Orbit5 [m]',
    'ALFA': 'Momentum compaction factor',
    'GAMMATR': 'Transition energy gamma',
    'DELTAP': 'Energy difference',
    'ENERGY': 'Particle energy [GeV]',
    'GAMMA': 'Particle gamma',

    'Q1': 'Horizontal tune (fractional)',
    'DQ1': 'Horizontal chromaticity',
    'BETXMIN': 'Horizontal minimum beta [m]',
    'BETXMAX': 'Horizontal maximum beta [m]',
    'DXMIN': 'Horizontal minimum dispersion [m]',
    'DXMAX': 'Horizontal maximum dispersion [m]',
    'DXRMS': 'Horizontal RMS dispersion [m]',
    'XCOMIN': 'Horizontal closed orbit minimum deviation [m]',
    'XCOMAX': 'Horizontal closed orbit maximum deviation [m]',
    'XCORMS': 'Horizontal closed orbit RMS deviation [m]',

    'Q2': 'Vertical tune (fractional)',
    'DQ2': 'Vertical chromaticity',
    'BETYMIN': 'Vertical minimum beta [m]',
    'BETYMAX': 'Vertical maximum beta [m]',
    'DYMIN': 'Vertical minimum dispersion [m]',
    'DYMAX': 'Vertical maximum dispersion [m]',
    'DYRMS': 'Vertical RMS dispersion [m]',
    'YCOMIN': 'Vertical closed orbit minimum deviation [m]',
    'YCOMAX': 'Vertical closed orbit maximum deviation [m]',
    'YCORMS': 'Vertical closed orbit RMS deviation [m]',
}


def background_percent_complete(report, run_dir, is_running):
    errors = ''
    if not is_running:
        out_file = run_dir.join('{}.json'.format(template_common.OUTPUT_BASE_NAME))
        count = 0
        if out_file.exists():
            out = simulation_db.read_json(out_file)
            if 'frame_count' in out:
                count = out.frame_count
        if not count:
            count = read_frame_count(run_dir)
        if count:
            return {
                'percentComplete': 100,
                'frameCount': count,
            }
        else:
            errors = _parse_zgoubi_log(run_dir)
    res = {
        'percentComplete': 0,
        'frameCount': 0,
    }
    if errors:
        res['errors'] = errors
    return res


def column_data(col, col_names, rows):
    idx = col_names.index(col)
    assert idx >= 0, 'invalid col: {}'.format(col)
    res = []
    for row in rows:
        res.append(float(row[idx]))
    return res


def extract_first_twiss_row(run_dir):
    col_names, rows = _read_data_file(py.path.local(run_dir).join(_ZGOUBI_TWISS_FILE))
    return col_names, rows[0]


def fixup_old_data(data):
    for m in [
            'bunch',
            'bunchAnimation',
            'bunchAnimation2',
            'energyAnimation',
            'particle',
            'particleCoordinate',
            'simulationSettings',
            'opticsReport',
            'twissReport',
            'twissReport2',
            'twissSummaryReport',
    ]:
        if m not in data.models:
            data.models[m] = pkcollections.Dict({})
        template_common.update_model_defaults(data.models[m], m, _SCHEMA)
    if 'coordinates' not in data.models.bunch:
        data.models.bunch.coordinates = []
    template_common.organize_example(data)


def get_animation_name(data):
    return 'animation'


def get_application_data(data):
    if data['method'] == 'compute_particle_ranges':
        return template_common.compute_field_range(data, _compute_range_across_frames)


def get_simulation_frame(run_dir, data, model_data):
    if re.search(r'bunchAnimation', data['modelName']) or data['modelName'] == 'energyAnimation':
        return _extract_animation(run_dir, data, model_data)
    assert False, 'invalid animation frame model: {}'.format(data['modelName'])


def lib_files(data, source_lib):
    return []


def models_related_to_report(data):
    r = data['report']
    if r == get_animation_name(data):
        return []
    res = ['particle', 'bunch']
    if 'bunchReport' in r:
        if data.models.bunch.match_twiss_parameters == '1':
            res.append('simulation.visualizationBeamlineId')
    res += [
        'beamlines',
        'elements',
    ]
    if r == 'twissReport':
        res.append('simulation.activeBeamlineId')
    if r == 'twissReport2' or 'opticsReport' in r or r == 'twissSummaryReport':
        res.append('simulation.visualizationBeamlineId')
    return res


def parse_error_log(run_dir):
    return None


def python_source_for_model(data, model):
    return _generate_parameters_file(data)


def prepare_output_file(run_dir, data):
    report = data['report']
    if 'bunchReport' in report or 'twissReport' in report or 'opticsReport' in report:
        fn = simulation_db.json_filename(template_common.OUTPUT_BASE_NAME, run_dir)
        if fn.exists():
            fn.remove()
            save_report_data(data, run_dir)


def read_frame_count(run_dir):
    data_file = run_dir.join(_ZGOUBI_DATA_FILE)
    if data_file.exists():
        col_names, rows = _read_data_file(data_file)
        ipasses = _ipasses_for_data(col_names, rows)
        return len(ipasses) + 1
    return 0


def remove_last_frame(run_dir):
    pass


def save_report_data(data, run_dir):
    report_name = data['report']
    if 'twissReport' in report_name or 'opticsReport' in report_name:
        enum_name = _REPORT_ENUM_INFO[report_name]
        report = data['models'][report_name]
        plots = []
        col_names, rows = _read_data_file(py.path.local(run_dir).join(_ZGOUBI_TWISS_FILE))
        for f in ('y1', 'y2', 'y3'):
            if report[f] == 'none':
                continue
            plots.append({
                'points': column_data(report[f], col_names, rows),
                'label': template_common.enum_text(_SCHEMA, enum_name, report[f]),
            })
        #TODO(pjm): use template_common
        x = column_data('sums', col_names, rows)
        res = {
            'title': '',
            'x_range': [min(x), max(x)],
            'y_label': '',
            'x_label': 's [m]',
            'x_points': x,
            'plots': plots,
            'y_range': template_common.compute_plot_color_and_range(plots),
            'summaryData': _read_twiss_header(run_dir),
        }
    elif report_name == 'twissSummaryReport':
        res = {
            #TODO(pjm): x_range requied by sirepo-plotting.js
            'x_range': [],
            'summaryData': _read_twiss_header(run_dir),
        }
    elif 'bunchReport' in report_name:
        report = data['models'][report_name]
        col_names, rows = _read_data_file(py.path.local(run_dir).join(_ZGOUBI_DATA_FILE))
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
    if 'opticsReport' in report_name or report_name == 'twissSummaryReport':
        return 'twissReport2'
    return report_name


def write_parameters(data, run_dir, is_parallel, python_file=template_common.PARAMETERS_PYTHON_FILE):
    pkio.write_text(
        run_dir.join(python_file),
        _generate_parameters_file(data),
    )


def _compute_range_across_frames(run_dir, data):
    res = {}
    for v in _SCHEMA.enum.PhaseSpaceCoordinate:
        res[v[0]] = []
    for v in _SCHEMA.enum.EnergyPlotVariable:
        res[v[0]] = []
    col_names, rows = _read_data_file(py.path.local(run_dir).join(_ZGOUBI_DATA_FILE))
    for field in res:
        values = column_data(field, col_names, rows)
        initial_field = _initial_phase_field(field)
        if initial_field in col_names:
            values += column_data(initial_field, col_names, rows)
        if len(res[field]):
            res[field][0] = min(min(values), res[field][0])
            res[field][1] = max(max(values), res[field][1])
        else:
            res[field] = [min(values), max(values)]
    for field in res.keys():
        factor = _ANIMATION_FIELD_INFO[field][1]
        res[field][0] *= factor
        res[field][1] *= factor
        res[_initial_phase_field(field)] = res[field]
    return res


def _element_value(el, field):
    converter = _MODEL_UNITS.get(el['type'], {}).get(field, None)
    return converter(el[field]) if converter else el[field]


def _extract_animation(run_dir, data, model_data):
    frame_index = int(data['frameIndex'])
    report = template_common.parse_animation_args(
        data,
        {
            '1': ['x', 'y', 'histogramBins', 'startTime'],
            '2': ['x', 'y', 'histogramBins', 'plotRangeType', 'horizontalSize', 'horizontalOffset', 'verticalSize', 'verticalOffset', 'isRunning', 'startTime'],
            '': ['x', 'y', 'histogramBins', 'plotRangeType', 'horizontalSize', 'horizontalOffset', 'verticalSize', 'verticalOffset', 'isRunning', 'showAllFrames', 'particleNumber', 'startTime'],
        },
    )
    is_frame_0 = False
    # fieldRange is store on the bunchAnimation
    model = model_data.models.bunchAnimation
    if data['modelName'] == 'energyAnimation':
        model.update(model_data.models.energyAnimation)
        frame_index += 1
    else:
        # bunchAnimations
        # remap frame 0 to use initial "o" values from frame 1
        if frame_index == 0:
            is_frame_0 = True
            for f in ('x', 'y'):
                report[f] = _initial_phase_field(report[f])
            frame_index = 1
    model.update(report)
    col_names, all_rows = _read_data_file(run_dir.join(_ZGOUBI_DATA_FILE))
    ipasses = _ipasses_for_data(col_names, all_rows)
    ipass = int(ipasses[frame_index - 1])
    rows = []
    ipass_index = int(col_names.index('IPASS'))
    let_index = int(col_names.index('LET'))
    let_search = "'{}'".format(report['particleNumber'])

    count = 0
    for row in all_rows:
        if report['showAllFrames'] == '1':
            if model_data.models.bunch.method == 'OBJET2.1' and report['particleNumber'] != 'all':
                if row[let_index] != let_search:
                    continue
            rows.append(row)
        elif int(row[ipass_index]) == ipass:
            rows.append(row)
    if report['showAllFrames'] == '1':
        title = 'All Frames'
        if model_data.models.bunch.method == 'OBJET2.1' and report['particleNumber'] != 'all':
            title += ', Particle {}'.format(report['particleNumber'])
    else:
        title = 'Initial Distribution' if is_frame_0 else 'Pass {}'.format(ipass)
    return _extract_bunch_data(model, col_names, rows, title)


def _extract_bunch_data(report, col_names, rows, title):
    x_info = _ANIMATION_FIELD_INFO[report['x']]
    y_info = _ANIMATION_FIELD_INFO[report['y']]
    x = np.array(column_data(report['x'], col_names, rows)) * x_info[1]
    y = np.array(column_data(report['y'], col_names, rows)) * y_info[1]
    return template_common.heatmap([x, y], report, {
        'x_label': x_info[0],
        'y_label': y_info[0],
        'title': title,
        'z_label': 'Number of Particles',
    });


def _generate_beamline(data, beamline_map, element_map, beamline_id):
    res = ''
    for item_id in beamline_map[beamline_id]['items']:
        if item_id in beamline_map:
            res += _generate_beamline(data, beamline_map, element_map, item_id)
            continue
        el = element_map[item_id]
        if el['type'] == 'AUTOREF':
            res += 'line.add(core.FAKE_ELEM(""" \'AUTOREF\'\n{}\n{} {} {}\n"""))\n'.format(
                el.I, _element_value(el, 'XCE'), _element_value(el, 'YCE'), _element_value(el, 'ALE'))
        elif el['type'] == 'CAVITE':
            form = 'line.add(core.FAKE_ELEM(""" \'CAVITE\'\n{}\n{} {} {}\n{} {} {}\n"""))\n'
            values = ['IOPT']
            if el.IOPT in ('0', '1', '2', '3'):
                values += ('L', 'h', '', 'V', 'sig_s', '')
            elif el.IOPT == '7':
                values += ('L', 'f_RF', '', 'V', 'sig_s', '')
            elif el.IOPT == '10':
                values += ('l', 'f_RF', 'ID', 'V', 'sig_s', 'IOP')
            res += form.format(*(map(lambda x: _element_value(el, x) if len(x) else '', values)))
        elif el['type'] == 'YMY':
            #TODO(pjm): looks like YMY is supported in pyzoubi?
            res += 'line.add(core.FAKE_ELEM(""" \'YMY\'\n"""))\n'
        elif el['type'] == 'SEXTUPOL':
            res += _generate_element(el, 'QUADRUPO')
        elif el['type'] == 'SCALING':
            form = 'line.add(core.FAKE_ELEM(""" \'SCALING\'\n{} {}\n{}"""))\n'
            _MAX_SCALING_FAMILY = 5
            count = 0
            scale_values = ''
            for idx in range(1, _MAX_SCALING_FAMILY + 1):
                # NAMEF1, SCL1
                if el['NAMEF{}'.format(idx)] != 'none':
                    count += 1
                    scale_values += '{}\n-1\n{}\n1\n'.format(el['NAMEF{}'.format(idx)], el['SCL{}'.format(idx)])
            if el.IOPT == '1' and count > 0:
                res += form.format(el.IOPT, count, scale_values)
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


def _generate_element(el, schema_type=None):
    res = 'line.add(core.{}("{}"'.format(el.type, el.name)
    for f in _SCHEMA.model[schema_type or el.type]:
        #TODO(pjm): need ignore list
        if f == 'name' or f == 'order' or f == 'format':
            continue
        res += ', {}={}'.format(_PYZGOUBI_FIELD_MAP.get(f, f), _element_value(el, f))
    res += '))\n'
    return res


def _generate_parameters_file(data):
    v = template_common.flatten_data(data.models, {})
    report = data.report if 'report' in data else ''
    v['particleDef'] = _generate_particle(data.models.particle)
    v['beamlineElements'] = _generate_beamline_elements(report, data)
    v['bunchCoordinates'] = data.models.bunch.coordinates
    res = template_common.render_jinja(SIM_TYPE, v, 'base.py')
    if 'twissReport' in report or 'opticsReport' in report or report == 'twissSummaryReport':
        return res + template_common.render_jinja(SIM_TYPE, v, 'twiss.py')
    v['outputFile'] = _ZGOUBI_DATA_FILE
    res += template_common.render_jinja(SIM_TYPE, v, 'bunch.py')
    if 'bunchReport' in report:
        return res + template_common.render_jinja(SIM_TYPE, v, 'bunch-report.py')
    return res + template_common.render_jinja(SIM_TYPE, v)


def _generate_particle(particle):
    if particle.particleType == 'Other':
        return '{} {} {} {} 0'.format(particle.M, particle.Q, particle.G, particle.Tau)
    return particle.particleType


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
        return str(_cm(float(v)))

    return {
        'AUTOREF': {
            'XCE': _cm,
            'YCE': _cm,
            'ALE': _mrad,
        },
        'BEND': {
            'l': _cm,
            'X_E': _cm,
            'LAM_E': _cm,
            'X_S': _cm,
            'LAM_S': _cm,
            'XPAS': _xpas,
            'XCE': _cm,
            'YCE': _cm,
        },
        'CAVITE': {
        },
        'CHANGREF': {
            'ALE': _degrees,
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
            'XPAS': _xpas,
            'LAM_S': _cm,
            'XCE': _cm,
            'YCE': _cm,
        },
        'SEXTUPOL': {
            'l': _cm,
            'R_0': _cm,
            'X_E': _cm,
            'LAM_E': _cm,
            'X_S': _cm,
            'XPAS': _xpas,
            'LAM_S': _cm,
            'XCE': _cm,
            'YCE': _cm,
        },
    }


def _initial_phase_field(field):
    return _INITIAL_PHASE_MAP.get(field, '{}o'.format(field))


def _ipasses_for_data(col_names, rows):
    res = []
    ipass_index = col_names.index('IPASS')
    for row in rows:
        ipass = row[ipass_index]
        if ipass not in res:
            res.append(ipass)
    return res


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


def _read_data_file(path):
    # mode: title -> header -> data
    mode = 'title'
    col_names = []
    rows = []
    with pkio.open_text(str(path)) as f:
        for line in f:
            if mode == 'title':
                if not re.search(r'^\@', line):
                    mode = 'header'
                continue
            # work-around odd header/value "! optimp.f" int twiss output
            line = re.sub(r'\!\s', '', line)
            # remove space from quoted values
            line = re.sub(r"'(\S*)\s*'", r"'\1'", line)
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


def _read_twiss_header(run_dir):
    path = py.path.local(run_dir).join(_ZGOUBI_TWISS_FILE)
    res = []
    for line in pkio.read_text(path).split('\n'):
        for var in line.split('@ '):
            values = var.split()
            if len(values) and values[0] in _TWISS_SUMMARY_LABELS:
                v = values[2]
                if re.search(r'[a-z]{2}', v, re.IGNORECASE):
                    pass
                else:
                    v = float(v)
                res.append([values[0], _TWISS_SUMMARY_LABELS[values[0]], v])
    return res


_MODEL_UNITS = _init_model_units()
