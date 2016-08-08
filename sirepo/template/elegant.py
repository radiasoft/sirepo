# -*- coding: utf-8 -*-
u"""elegant execution template.

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkio
from pykern import pkjinja
from pykern import pkresource
from sirepo import simulation_db
from sirepo.template import elegant_lattice_importer
from sirepo.template import template_common
import glob
import numpy as np
import os
import os.path
import py.path
import re
import sdds
import shutil
import time
import werkzeug

ELEGANT_LOG_FILE = 'elegant.log'

WANT_BROWSER_FRAME_CACHE = True

_ELEGANT_ME_EV = 0.51099906e6

_ELEGANT_CENTROID_OUTPUT_FILE = 'centroid-output.sdds'

_ELEGANT_FINAL_OUTPUT_FILE = 'elegant-final-output.sdds'

_ELEGANT_PARAMETERS_FRAME_ID = -2

_ELEGANT_PARAMETERS_OUTPUT_FILE = 'elegant-parameters.sdds'

_ELEGANT_SIGMA_OUTPUT_FILE = 'sigma-matrix.sdds'

_ELEGANT_TWISS_OUTPUT_FILE = 'twiss-parameters.sdds'

_STANDARD_OUTPUT_FILE_ID = 0

_STANDARD_OUTPUT_FILE_INDEX = {
    _ELEGANT_FINAL_OUTPUT_FILE: 1,
    _ELEGANT_TWISS_OUTPUT_FILE: 2,
    _ELEGANT_CENTROID_OUTPUT_FILE: 3,
    _ELEGANT_SIGMA_OUTPUT_FILE: 4,
}

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

_SDDS_INDEX = 0

_STATIC_FOLDER = py.path.local(pkresource.filename('static'))

_SCHEMA = simulation_db.read_json(_STATIC_FOLDER.join('json/elegant-schema'))


def background_percent_complete(report, run_dir, is_running, schema):
    errors, last_element = _parse_elegant_log(run_dir)
    res = {
        'percent_complete': 100,
        'frame_count': 0,
        'errors': errors,
    }
    if is_running:
        data = simulation_db.read_json(run_dir.join(template_common.INPUT_BASE_NAME))
        res['last_update_time'] = int(time.time())
        res['percent_complete'] = _compute_percent_complete(data, last_element)
        res['start_time'] = data['models']['simulationStatus'][report]['startTime']
        return res
    if not _has_elegant_output(run_dir):
        res['state'] = 'initial'
        return res
    if not _has_valid_elegant_output(run_dir):
        return res
    data = simulation_db.read_json(run_dir.join(template_common.INPUT_BASE_NAME))
    output_info = _output_info(run_dir, data, schema)
    return {
        'percent_complete': 100,
        'frame_count': 1,
        'output_info': output_info,
        'last_update_time': output_info[0]['last_update_time'],
        'start_time': data['models']['simulationStatus'][report]['startTime'],
        'errors': errors,
    }


def copy_related_files(data, source_path, target_path):
    # copy any simulation output
    if os.path.isdir(str(py.path.local(source_path).join('animation'))):
        animation_dir = py.path.local(target_path).join('animation')
        pkio.mkdir_parent(str(animation_dir))
        for f in glob.glob(str(py.path.local(source_path).join('animation', '*'))):
            shutil.copy(f, str(animation_dir))
    # copy element InputFiles to lib
    #TODO(pjm): assumes the location of the lib directory
    source_lib = py.path.local(os.path.dirname(source_path)).join('lib')
    target_lib = py.path.local(os.path.dirname(target_path)).join('lib')
    lib_files = []
    for el in data['models']['elements']:
        model_schema = _SCHEMA['model'][el['type']]
        for k in el:
            if k not in model_schema:
                continue
            element_schema = model_schema[k]
            if el[k] and element_schema[1].startswith('InputFile'):
                #TODO(pjm): need a common formatter for file names
                lib_files.append('{}-{}.{}'.format(el['type'], k, el[k]))
    if data['models']['bunchFile']['sourceFile']:
        lib_files.append('{}-{}.{}'.format('bunchFile', 'sourceFile', data['models']['bunchFile']['sourceFile']))
    for f in lib_files:
        target = target_lib.join(f)
        if not target.exists():
            shutil.copy(str(source_lib.join(f)), str(target))


def extract_report_data(filename, data, p_central_mev, page_index):
    xfield = data['x']
    yfield = data['y']
    bins = data['histogramBins']
    if sdds.sddsdata.InitializeInput(_SDDS_INDEX, filename) != 1:
        return _sdds_error()
    column_names = sdds.sddsdata.GetColumnNames(_SDDS_INDEX)
    count = page_index
    while count >= 0:
        if sdds.sddsdata.ReadPage(_SDDS_INDEX) <= 0:
            break
        count -= 1
    try:
        x = sdds.sddsdata.GetColumn(_SDDS_INDEX, column_names.index(xfield))
    except SystemError as e:
        return _sdds_error()

    if xfield == 'p':
        x = _scale_p(x, p_central_mev)
    y = sdds.sddsdata.GetColumn(_SDDS_INDEX, column_names.index(yfield))
    if yfield == 'p':
        y = _scale_p(y, p_central_mev)

    if _is_2d_plot(column_names):
        # 2d plot
        sdds.sddsdata.Terminate(_SDDS_INDEX)
        return {
            'title': _plot_title(xfield, yfield, page_index),
            'x_range': [np.min(x), np.max(x)],
            'x_label': _field_label(xfield),
            'y_label': _field_label(yfield),
            'points': y,
            'x_points': x,
        }

    nbins = int(bins)
    hist, edges = np.histogramdd([x, y], nbins)
    sdds.sddsdata.Terminate(_SDDS_INDEX)
    return {
        'x_range': [float(edges[0][0]), float(edges[0][-1]), len(hist)],
        'y_range': [float(edges[1][0]), float(edges[1][-1]), len(hist[0])],
        'x_label': _field_label(xfield),
        'y_label': _field_label(yfield),
        'title': _plot_title(xfield, yfield, page_index),
        'z_matrix': hist.T.tolist(),
    }


def fixup_old_data(data):
    if 'bunchSource' not in data['models']:
        data['models']['bunchSource'] = {
            'inputSource': 'bunched_beam',
        }
    if 'bunchFile' not in data['models']:
        data['models']['bunchFile'] = {
            'sourceFile': None,
        }
    if 'folder' not in data['models']['simulation']:
        data['models']['simulation']['folder'] = '/'


def generate_lattice(data, v):
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
            if k in ['name', 'type', '_id'] or re.search('(X|Y)$', k):
                continue
            value = el[k]
            element_schema = _SCHEMA['model'][el['type']][k]
            default_value = element_schema[2]
            if value is not None and default_value is not None:
                if str(value) != str(default_value):
                    if element_schema[1].startswith('InputFile'):
                        value = '{}-{}.{}'.format(el['type'], k, value)
                        if element_schema[1] == 'InputFileXY':
                            value += '={}+{}'.format(el[k + 'X'], el[k + 'Y'])
                    res += '{}="{}",'.format(k, value)
        res = res[:-1]
        res += "\n"

    for bl in ordered_beamlines:
        if len(bl['items']):
            res += '"{}": LINE=('.format(bl['name'].upper())
            for id in bl['items']:
                sign = ''
                if id < 0:
                    sign = '-'
                    id = abs(id)
                res += '{},'.format(sign + names[id].upper())
            res = res[:-1]
            res += ")\n"

    return res


def generate_parameters_file(data, schema, run_dir=None, run_async=False):
    _validate_data(data, schema)
    v = template_common.flatten_data(data['models'], {})
    v['elegantFinalOutput'] = _ELEGANT_FINAL_OUTPUT_FILE
    v['elegantCentroidOutput'] = _ELEGANT_CENTROID_OUTPUT_FILE
    v['elegantSigmaOutput'] = _ELEGANT_SIGMA_OUTPUT_FILE
    v['elegantParameterOutput'] = _ELEGANT_PARAMETERS_OUTPUT_FILE
    v['elegantTwissOutput'] = _ELEGANT_TWISS_OUTPUT_FILE
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
    if data['models']['bunchSource']['inputSource'] == 'sdds_beam':
        v['bunch_beta_x'] = 5
        v['bunch_beta_y'] = 5
        v['bunch_alpha_x'] = 0
        v['bunch_alpha_x'] = 0
    if run_async:
        v['lattice'] = generate_lattice(data, v)
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
        if frame == _ELEGANT_PARAMETERS_FRAME_ID:
            path = str(run_dir.join(_ELEGANT_PARAMETERS_OUTPUT_FILE))
            with open(path) as f:
                return _ELEGANT_PARAMETERS_OUTPUT_FILE, f.read(), 'application/octet-stream'
        path = str(run_dir.join(ELEGANT_LOG_FILE))
        with open(path) as f:
            return 'elegant-output.txt', f.read(), 'text/plain'

    if model == 'beamlineReport':
        data = simulation_db.read_json(str(run_dir.join('..', simulation_db.SIMULATION_DATA_FILE)))
        source = generate_parameters_file(data, _SCHEMA, run_async=True)
        return 'python-source.py', source, 'text/plain'

    for path in glob.glob(str(run_dir.join('elegant.bun'))):
        path = str(py.path.local(path))
        with open(path) as f:
            return os.path.basename(path), f.read(), 'application/octet-stream'
    raise RuntimeError('no datafile found in run_dir: {}'.format(run_dir))


def import_file(request, lib_dir=None, tmp_dir=None):
    f = request.files['file']
    try:
        data = elegant_lattice_importer.import_file(f.read())
        name = re.sub(r'\.lte$', '', werkzeug.secure_filename(f.filename), re.IGNORECASE)
        data['models']['simulation']['name'] = name
        return None, data
    except IOError as e:
        return e.message, None


def is_cache_valid(data, old_data):
    if 'bunchReport' in data['report']:
        for name in [data['report'], 'bunch', 'simulation', 'bunchSource', 'bunchFile']:
            if data['models'][name] != old_data['models'][name]:
                return False
        return True
    return False


def new_simulation(data, new_simulation_data):
    pass


def prepare_aux_files(run_dir, data):
    pass


def prepare_for_client(data):
    return data


def remove_last_frame(run_dir):
    pass


def run_all_text():
    return '''
with open('elegant.lte', 'w') as f:
    f.write(lattice_file)

with open('elegant.ele', 'w') as f:
    f.write(elegant_file)

import os
os.system('elegant elegant.ele')
'''


def static_lib_files():
    """Library shared between simulations of this type

    Returns:
        list: py.path.local objects
    """
    res = []
    for f in glob.glob(str(_STATIC_FOLDER.join('dat', '*.sdds'))):
        res.append(py.path.local(f))
    return res


def validate_file(file_type, path):
    err = None
    if file_type == 'bunchFile-sourceFile':
        err = 'expecting sdds file with x, xp, y, yp, t and p columns'
        if sdds.sddsdata.InitializeInput(_SDDS_INDEX, path) == 1:
            column_names = sdds.sddsdata.GetColumnNames(_SDDS_INDEX)
            has_columns = True
            for col in ['x', 'xp', 'y', 'yp', 't', 'p']:
                if col not in column_names:
                    has_columns = False
                    break
            if has_columns:
                sdds.sddsdata.ReadPage(_SDDS_INDEX)
                if len(sdds.sddsdata.GetColumn(_SDDS_INDEX, column_names.index('x'))) > 0:
                    err = None
                else:
                    err = 'sdds file contains no rows'
        sdds.sddsdata.Terminate(_SDDS_INDEX)
    return err


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
        id = abs(id)
        if id in beamlines:
            _add_beamlines(beamlines[id], beamlines, ordered_beamlines)
    ordered_beamlines.append(beamline)


def _compute_percent_complete(data, last_element):
    if not last_element:
        return 0
    elements = {}
    for e in data['models']['elements']:
        elements[e['_id']] = e
    beamlines = {}
    for b in data['models']['beamlines']:
        beamlines[b['id']] = b
    id = data['models']['simulation']['visualizationBeamlineId']
    beamline_map = {}
    count = _walk_beamline(beamlines[id], 1, elements, beamlines, beamline_map)
    index = beamline_map[last_element] if last_element in beamline_map else 0
    res = index * 100 / count
    if res > 100:
        return 100
    return res


def _field_label(field):
    if field in _FIELD_LABEL:
        return _FIELD_LABEL[field]
    return field


def _file_info(filename, run_dir, id, output_index):
    file_path = run_dir.join(filename)
    if sdds.sddsdata.InitializeInput(_SDDS_INDEX, str(file_path)) != 1:
        sdds.sddsdata.Terminate(_SDDS_INDEX)
        return {}
    column_names = sdds.sddsdata.GetColumnNames(_SDDS_INDEX)
    page_count = 1

    page = sdds.sddsdata.ReadPage(_SDDS_INDEX)
    while page > 0:
        page = sdds.sddsdata.ReadPage(_SDDS_INDEX)
        if page > 0:
            page_count += 1
    sdds.sddsdata.Terminate(_SDDS_INDEX)
    return {
        'filename': filename,
        'id': '{}-{}'.format(id, output_index),
        'page_count': page_count,
        'columns': column_names,
        'last_update_time': os.path.getmtime(str(file_path)),
    }


def _get_filename_for_element_id(id, data):
    filename = _ELEGANT_FINAL_OUTPUT_FILE
    if id[0] == str(_STANDARD_OUTPUT_FILE_ID):
        for k in _STANDARD_OUTPUT_FILE_INDEX:
            if id[1] == str(_STANDARD_OUTPUT_FILE_INDEX[k]):
                return k

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


def _has_elegant_output(run_dir):
    path = run_dir.join(_ELEGANT_FINAL_OUTPUT_FILE)
    return path.exists()


def _has_valid_elegant_output(run_dir):
    path = run_dir.join(_ELEGANT_FINAL_OUTPUT_FILE)
    if not path.exists():
        return False
    file_ok = False
    if sdds.sddsdata.InitializeInput(_SDDS_INDEX, str(path)) == 1:
        sdds.sddsdata.ReadPage(_SDDS_INDEX)
        try:
            sdds.sddsdata.GetColumn(_SDDS_INDEX, 0)
            file_ok = True
        except SystemError as e:
            pass
    sdds.sddsdata.Terminate(_SDDS_INDEX)
    return file_ok


#TODO(pjm): keep in sync with elegant.js reportTypeForColumns()
def _is_2d_plot(columns):
    if ('x' in columns and 'xp' in columns) \
       or ('y' in columns and 'yp' in columns) \
       or ('t' in columns and 'p' in columns):
        return False
    return True


def _is_error_text(text):
    return re.search(r'^warn|^error|wrong units|^fatal error|no expansion for entity|unable to find|warning\:|^0 particles left', text, re.IGNORECASE)


def _output_info(run_dir, data, schema):
    res = [
        _standard_file_info(_ELEGANT_FINAL_OUTPUT_FILE, run_dir),
        _standard_file_info(_ELEGANT_TWISS_OUTPUT_FILE, run_dir),
        _standard_file_info(_ELEGANT_CENTROID_OUTPUT_FILE, run_dir),
        _standard_file_info(_ELEGANT_SIGMA_OUTPUT_FILE, run_dir),
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
                res.append(_file_info(value, run_dir, el['_id'], field_index))
    return res


def _parse_elegant_log(run_dir):
    path = run_dir.join(ELEGANT_LOG_FILE)
    if not path.exists():
        return '', 0
    res = ''
    last_element = None
    text = pkio.read_text(str(path))
    want_next_line = False
    for line in text.split("\n"):
        match = re.search('^Starting (\S+) at s\=', line)
        if match:
            name = match.group(1)
            if not re.search('^M\d+\#', name):
                last_element = name
        if want_next_line:
            res += line + "\n"
            want_next_line = False
        elif _is_error_text(line):
            if len(line) < 10:
                want_next_line = True
            else:
                res += line + "\n"
    return res, last_element


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


def _sdds_error():
    sdds.sddsdata.Terminate(_SDDS_INDEX)
    return {
        'error': 'invalid data file',
    }


def _standard_file_info(filename, run_dir):
    return _file_info(filename, run_dir, _STANDARD_OUTPUT_FILE_ID, int(_STANDARD_OUTPUT_FILE_INDEX[filename]))


def _validate_data(data, schema):
    # ensure enums match, convert ints/floats, apply scaling
    enum_info = template_common.parse_enums(schema['enum'])
    for k in data['models']:
        if k in schema['model']:
            template_common.validate_model(data['models'][k], schema['model'][k], enum_info)


def _walk_beamline(beamline, index, elements, beamlines, beamline_map):
    # walk beamline in order, adding (<name>#<count> => index) to beamline_map
    for id in beamline['items']:
        if id in elements:
            name = elements[id]['name']
            if name not in beamline_map:
                beamline_map[name] = 0
            beamline_map[name] += 1
            beamline_map['{}#{}'.format(name.upper(), beamline_map[name])] = index
            index += 1
        else:
            index = _walk_beamline(beamlines[abs(id)], index, elements, beamlines, beamline_map)
    return index
