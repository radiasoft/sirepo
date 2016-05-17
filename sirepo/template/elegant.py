# -*- coding: utf-8 -*-
u"""elegant execution template.

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkio
from pykern import pkjinja
from sirepo import simulation_db
from sirepo.template import template_common
import glob
import numpy as np
import os
import py.path
import re
import sdds
import time

ELEGANT_LOG_FILE = 'elegant.stdout'

ELEGANT_STDERR_FILE = 'elegant.stderr'

WANT_BROWSER_FRAME_CACHE = True

_ELEGANT_ME_EV = 0.51099906e6

_ELEGANT_FINAL_OUTPUT_FILE = 'elegant.out'

_FIELD_LABEL = {
    'x': 'x [m]',
    'xp': "x' [rad]",
    'y': 'y [m]',
    'yp': "y' [rad]",
    't': 't [s]',
    'p': '(p - p₀)/p₀ [eV]',
    's': 's [m]',
    'LinearDensity': 'Linear Density [C/s]',
    'LinearDensityDeriv': 'LinearDensityDeriv [C/s²]',
    'GammaDeriv': 'GammaDeriv [1/m]',
}

_PLOT_TITLE = {
    'x-xp': 'Horizontal',
    'y-yp': 'Vertical',
    'x-y': 'Cross-section',
    't-p': 'Longitudinal',
}


def _has_valid_elegant_output(run_dir):
    path = run_dir.join(_ELEGANT_FINAL_OUTPUT_FILE)
    if not path.exists():
        return False
    file_ok = False
    if sdds.sddsdata.InitializeInput(0, str(path)) == 1:
        if sdds.sddsdata.ReadPage(0) == 1:
            file_ok = True
    sdds.sddsdata.Terminate(0)
    return file_ok


def _is_error_text(text):
    return re.search(r'^warn|^error|wrong units|^fatal error|no expansion for entity', text, re.IGNORECASE)


def _parse_errors_from_log(run_dir):
    #TODO(pjm): also check ELEGANT_STDERR_FILE
    path = run_dir.join(ELEGANT_LOG_FILE)
    if not path.exists():
        return ''
    res = ''
    text = pkio.read_text(str(path))
    want_next_line = False
    for line in text.split("\n"):
        if want_next_line:
            res += line + "\n"
            want_next_line = False
        elif _is_error_text(line):
            if len(line) < 10:
                want_next_line = True
            else:
                res += line + "\n"
    return res


def background_percent_complete(data, run_dir, is_running, schema):
    if is_running or not _has_valid_elegant_output(run_dir):
        res = {
            'percent_complete': 100,
            'frame_count': 0,
            'errors': _parse_errors_from_log(run_dir),
        }
        if is_running:
            res['last_update_time'] = int(time.time())
        return res
    output_info = [
        _file_info(_ELEGANT_FINAL_OUTPUT_FILE, run_dir, 0, 1),
    ]

    for el in data['models']['elements']:
        model_schema = schema['model'][el['type']]
        field_index = 0
        for k in sorted(el.iterkeys()):
            field_index += 1
            value = el[k]
            if not value or k not in model_schema:
                continue
            element_schema = model_schema[k]
            #TODO(pjm): iterate active beamline elements and remove exists() check
            if element_schema[1] == 'OutputFile' and run_dir.join(value).exists():
                output_info.append(_file_info(value, run_dir, el['_id'], field_index))
    return {
        'percent_complete': 100,
        'frame_count': 1,
        'output_info': output_info,
        'last_update_time': output_info[0]['last_update_time'],
    }


def copy_animation_file(source_path, target_path):
    pass


def extract_report_data(filename, data, p_central_mev, page_index):
    xfield = data['x']
    yfield = data['y']
    bins = data['histogramBins']

    index = 0
    if sdds.sddsdata.InitializeInput(index, filename) != 1:
        sdds.sddsdata.PrintErrors(1)
    column_names = sdds.sddsdata.GetColumnNames(index)
    count = page_index
    while count >= 0:
        errorCode = sdds.sddsdata.ReadPage(index)
        if errorCode != 1:
            sdds.sddsdata.PrintErrors(1)
        count -= 1
    x = sdds.sddsdata.GetColumn(index, column_names.index(xfield))
    if xfield == 'p':
        x = _scale_p(x, p_central_mev)
    y = sdds.sddsdata.GetColumn(index, column_names.index(yfield))
    if yfield == 'p':
        y = _scale_p(y, p_central_mev)

    if column_names[0] == 's':
        # 2d plot
        return {
            'title': _plot_title(xfield, yfield, page_index),
            'x_range': [np.min(x), np.max(x)],
            'x_label': _field_label(xfield),
            'y_label': _field_label(yfield),
            'points': y,
        }

    nbins = int(bins)
    hist, edges = np.histogramdd([x, y], nbins)
    if sdds.sddsdata.Terminate(index) != 1:
        sdds.sddsdata.PrintErrors(1)
    return {
        'x_range': [float(edges[0][0]), float(edges[0][-1]), len(hist)],
        'y_range': [float(edges[1][0]), float(edges[1][-1]), len(hist[0])],
        'x_label': _field_label(xfield),
        'y_label': _field_label(yfield),
        'title': _plot_title(xfield, yfield, page_index),
        'z_matrix': hist.T.tolist(),
    }

def _field_label(field):
    if field in _FIELD_LABEL:
        return _FIELD_LABEL[field]
    return field

def fixup_old_data(data):
    if 'bunchReport4' not in data['models']:
        data['models']['bunchReport1'] = {
            'x': 'x',
            'y': 'xp',
            'histogramBins': 200,
        }
        data['models']['bunchReport2'] = {
            'x': 'y',
            'y': 'yp',
            'histogramBins': 200,
        }
        data['models']['bunchReport3'] = {
            'x': 'x',
            'y': 'y',
            'histogramBins': 200,
        }
        data['models']['bunchReport4'] = {
            'x': 't',
            'y': 'p',
            'histogramBins': 200,
        }
    if 'longitudinalMethod' not in data['models']['bunch']:
        bunch = data['models']['bunch']
        bunch['longitudinalMethod'] = '1'
        bunch['dp_s_coupling'] = 0
        bunch['alpha_z'] = 0
        bunch['beta_z'] = 0
        bunch['emit_z'] = 0
    if 'beamlines' not in data['models']:
        data['models']['beamlines'] = []
    if 'elements' not in data['models']:
        data['models']['elements'] = []
    if 'simulationStatus' not in data['models']:
        data['models']['simulationStatus'] = {
            'animation': {
                'state': 'initial',
            },
        }
    if 'animation' not in data['models']['simulationStatus']:
        data['models']['simulationStatus'] = {
            'animation': {
                'state': 'initial',
            },
        }
    if 'beamlineReport' not in data['models']:
        data['models']['beamlineReport'] = {}


def generate_parameters_file(data, schema, run_dir=None, run_async=False):
    _validate_data(data, schema)
    v = template_common.flatten_data(data['models'], {})
    v['elegantFinalOutput'] = _ELEGANT_FINAL_OUTPUT_FILE
    longitudinal_method = int(data['models']['bunch']['longitudinalMethod'])
    if longitudinal_method == 1:
        v['bunch_emit_z'] = 0
        v['bunch_beta_z'] = 0
        v['bunch_alpha_z'] = 0
    elif longitudinal_method == 2:
        v['bunch_emit_z'] = 0
        v['bunch_beta_z'] = 0
        v['bunch_dp_s_coupling'] = 0
    elif longitudinal_method == 3:
        v['bunch_sigma_dp'] = 0
        v['bunch_sigma_s'] = 0
        v['bunch_dp_s_coupling'] = 0
    if run_async:
        v['lattice'] = _generate_lattice(data, schema, v)
    else:
        # use a dummy lattice with a 0 length drift for generating bunches
        v['use_beamline'] = 'bl'
        v['lattice'] = '''
d: drift,l=0
bl: line=(d)
'''
    return pkjinja.render_resource('elegant.py', v)


def get_animation_name(data):
    return 'animation'


def get_simulation_frame(run_dir, data, model_data):
    frame_index = int(data['frameIndex'])
    args = data['animationArgs'].split('_')
    frame_data = {
        'x': args[0],
        'y': args[1],
        'histogramBins': args[2],
    }
    id = args[3].split('-')
    filename = _get_filename_for_element_id(id, model_data)
    return extract_report_data(str(run_dir.join(filename)), frame_data, model_data['models']['bunch']['p_central_mev'], frame_index)


def _get_filename_for_element_id(id, data):
    filename = _ELEGANT_FINAL_OUTPUT_FILE

    for el in data['models']['elements']:
        if str(el['_id']) != id[0]:
            continue
        field_index = 0
        for k in sorted(el.iterkeys()):
            field_index += 1
            if str(field_index) == id[1]:
                filename = el[k]
                break
    return filename


def get_data_file(run_dir, model, frame):
    if frame >= 0:
        data = simulation_db.read_json(run_dir.join(template_common.INPUT_BASE_NAME))
        # ex. elementAnimation17-55
        id = re.sub(r'elementAnimation', '', model).split('-')
        filename = _get_filename_for_element_id(id, data)
        path = str(run_dir.join(filename))
        with open(path) as f:
            return os.path.basename(path), f.read(), 'application/octet-stream'

    if model == 'animation':
        path = str(run_dir.join(ELEGANT_LOG_FILE))
        with open(path) as f:
            return 'elegant-output.txt', f.read(), 'text/plain'

    for path in glob.glob(str(run_dir.join('elegant.bun'))):
        path = str(py.path.local(path))
        with open(path) as f:
            return os.path.basename(path), f.read(), 'application/octet-stream'
    raise RuntimeError('no datafile found in run_dir: {}'.format(run_dir))


def is_cache_valid(data, old_data):
    if 'bunchReport' in data['report']:
        for name in [data['report'], 'bunch', 'simulation']:
            if data['models'][name] != old_data['models'][name]:
                return False
        return True
    return False


def new_simulation(data, new_simulation_data):
    pass


def prepare_aux_files(run_dir, data):
    pass


def remove_last_frame(run_dir):
    pass


def run_all_text():
    return '''
'''


def static_lib_files():
    """Library shared between simulations of this type

    Returns:
        list: py.path.local objects
    """
    return []


def write_parameters(data, schema, run_dir, run_async):
    """Write the parameters file

    Args:
        data (dict): input
        schema (dict): to validate data
        run_dir (py.path): where to write
        run_async (bool): run in background?
    """
    pkio.write_text(
        run_dir.join(template_common.PARAMETERS_PYTHON_FILE),
        generate_parameters_file(
            data,
            schema,
            run_dir,
            run_async,
        ),
    )


def _add_beamlines(beamline, beamlines, ordered_beamlines):
    if beamline in ordered_beamlines:
        return
    for id in beamline['items']:
        if id in beamlines:
            _add_beamlines(beamlines[id], beamlines, ordered_beamlines)
    ordered_beamlines.append(beamline)


def _file_info(filename, run_dir, id, output_index):
    file_path = run_dir.join(filename)
    index = 0
    if sdds.sddsdata.InitializeInput(index, str(file_path)) != 1:
        sdds.sddsdata.PrintErrors(1)
        return {}
    column_names = sdds.sddsdata.GetColumnNames(index)
    page_count = 1

    page = sdds.sddsdata.ReadPage(index)
    if page != 1:
        sdds.sddsdata.PrintErrors(1)
    while page > 0:
        page = sdds.sddsdata.ReadPage(index)
        if page > 0:
            page_count += 1
    sdds.sddsdata.Terminate(index)
    return {
        'filename': filename,
        'id': '{}-{}'.format(id, output_index),
        'page_count': page_count,
        'columns': column_names,
        'last_update_time': os.path.getmtime(str(file_path)),
    }


def _generate_lattice(data, schema, v):
    res = ''
    names = {}
    beamlines = {}

    for bl in data['models']['beamlines']:
        if 'visualizationBeamlineId' in data['models']['simulation']:
            if int(data['models']['simulation']['visualizationBeamlineId']) == int(bl['id']):
                v['use_beamline'] = bl['name']
        names[bl['id']] = bl['name']
        beamlines[bl['id']] = bl

    ordered_beamlines = []

    for id in beamlines:
        _add_beamlines(beamlines[id], beamlines, ordered_beamlines)

    for el in data['models']['elements']:
        res += '"{}": {},'.format(el['name'].upper(), el['type'])
        names[el['_id']] = el['name']

        for k in el:
            if k in ['name', 'type', '_id']:
                continue
            value = el[k]
            element_schema = schema['model'][el['type']][k]
            default_value = element_schema[2]
            if value is not None and default_value is not None:
                if str(value) != str(default_value):
                    if element_schema[1] == 'InputFile':
                        value = '{}-{}.{}'.format(el['type'], k, value)
                    res += '{}="{}",'.format(k, value)
        res = res[:-1]
        res += "\n"

    for bl in ordered_beamlines:
        if len(bl['items']):
            res += '"{}": LINE=('.format(bl['name'].upper())
            for id in bl['items']:
                res += '{},'.format(names[id].upper())
            res = res[:-1]
            res += ")\n"

    return res


def _plot_title(xfield, yfield, page_index):
    key = '{}-{}'.format(xfield, yfield)
    title = ''
    if key in _PLOT_TITLE:
        title = _PLOT_TITLE[key]
    else:
        title = '{} / {}'.format(xfield, yfield)
    if page_index:
        title += ', Plot ' + str(page_index + 1)
    return title


def _scale_p(points, p_central_mev):
    p_central_ev = float(p_central_mev) * 1e6
    return (np.array(points) * _ELEGANT_ME_EV - p_central_ev).tolist()


def _validate_data(data, schema):
    # ensure enums match, convert ints/floats, apply scaling
    enum_info = template_common.parse_enums(schema['enum'])
    for k in data['models']:
        if k in schema['model']:
            template_common.validate_model(data['models'][k], schema['model'][k], enum_info)
