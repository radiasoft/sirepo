# -*- coding: utf-8 -*-
u"""elegant execution template.

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkio
from pykern import pkjinja
from pykern import pkresource
from pykern.pkdebug import pkdp, pkdc
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
import subprocess
import werkzeug

ELEGANT_LOG_FILE = 'elegant.log'

WANT_BROWSER_FRAME_CACHE = True

_ELEGANT_SEMAPHORE_FILE = 'run_setup.semaphore'

_RPN_DEFN_FILE = str(py.path.local(pkresource.filename('defns.rpn')))

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

_SDDS_DOUBLE_TYPE = 1

_SDDS_STRING_TYPE = 7

_STATIC_FOLDER = py.path.local(pkresource.filename('static'))

_SCHEMA = simulation_db.get_schema('elegant')

_ELEGANT_ME_EV = _SCHEMA['constant']['ELEGANT_ME_EV']


def background_percent_complete(report, run_dir, is_running, schema):
    #TODO(robnagler) remove duplication in run_dir.exists() (outer level?)
    errors, last_element = _parse_elegant_log(run_dir)
    res = {
        'percentComplete': 100,
        'frameCount': 0,
        'errors': errors,
    }
    if is_running:
        data = simulation_db.read_json(run_dir.join(template_common.INPUT_BASE_NAME))
        res['percentComplete'] = _compute_percent_complete(data, last_element)
        return res
    if not run_dir.join(_ELEGANT_SEMAPHORE_FILE).exists():
        return res
    data = simulation_db.read_json(run_dir.join(template_common.INPUT_BASE_NAME))
    output_info = _output_info(run_dir, data, schema)
    return {
        'percentComplete': 100,
        'frameCount': 1,
        'outputInfo': output_info,
        'lastUpdateTime': output_info[0]['lastUpdateTime'],
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
    _iterate_model_fields(data, lib_files, _iterator_input_files)

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
        return _sdds_error('no data for page {}'.format(page_index))

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
    if 'rpnVariables' not in data['models']:
        data['models']['rpnVariables'] = []
    if 'commands' not in data['models']:
        data['models']['commands'] = _create_default_commands(data)
        for m in data['models']['elements']:
            model_schema = _SCHEMA['model'][m['type']]
            for k in m:
                if k in model_schema and model_schema[k][1] == 'OutputFile' and m[k]:
                    m[k] = "1"
    for m in data['models']['elements']:
        if m['type'] == 'WATCH' and (m['mode'] == 'coordinates' or m['mode'] == 'coord'):
            m['mode'] = 'coordinate'


def generate_lattice(data, filename_map, beamline_map, v):
    beamlines = {}

    for bl in data['models']['beamlines']:
        if 'visualizationBeamlineId' in data['models']['simulation']:
            if int(data['models']['simulation']['visualizationBeamlineId']) == int(bl['id']):
                v['use_beamline'] = bl['name']
        beamlines[bl['id']] = bl

    ordered_beamlines = []

    for id in beamlines:
        _add_beamlines(beamlines[id], beamlines, ordered_beamlines)
    state = {
        'lattice': '',
        'beamline_map': beamline_map,
        'filename_map': filename_map,
    }
    _iterate_model_fields(data, state, _iterator_lattice_elements)
    res = state['lattice']
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
                res += '{},'.format(sign + beamline_map[id].upper())
            res = res[:-1]
            res += ")\n"

    return res


def generate_parameters_file(data, schema, run_dir=None, is_parallel=False):
    _validate_data(data, schema)
    v = template_common.flatten_data(data['models'], {})
    longitudinal_method = int(data['models']['bunch']['longitudinalMethod'])

    # sigma s, sigma dp, dp s coupling
    if longitudinal_method == 1:
        v['bunch_emit_z'] = 0
        v['bunch_beta_z'] = 0
        v['bunch_alpha_z'] = 0
    # sigma s, sigma dp, alpha z
    elif longitudinal_method == 2:
        v['bunch_emit_z'] = 0
        v['bunch_beta_z'] = 0
        v['bunch_dp_s_coupling'] = 0
    # emit z, beta z, alpha z
    elif longitudinal_method == 3:
        v['bunch_sigma_dp'] = 0
        v['bunch_sigma_s'] = 0
        v['bunch_dp_s_coupling'] = 0
    if data['models']['bunchSource']['inputSource'] == 'sdds_beam':
        v['bunch_beta_x'] = 5
        v['bunch_beta_y'] = 5
        v['bunch_alpha_x'] = 0
        v['bunch_alpha_x'] = 0
    v['rpn_variables'] = _generate_variables(data)

    if is_parallel:
        filename_map = _build_filename_map(data)
        beamline_map = _build_beamline_map(data)
        v['commands'] = _generate_commands(data, filename_map, beamline_map, v)
        v['lattice'] = generate_lattice(data, filename_map, beamline_map, v)
        return pkjinja.render_resource('elegant.py', v)

    return pkjinja.render_resource('elegant_bunch.py', v)


def get_animation_name(data):
    return 'animation'


def get_application_data(data):
    if data['method'] == 'rpn_value':
        value, error = parse_rpn_value(data['value'], data['variables'])
        if error:
            data['error'] = error
        else:
            data['result'] = value
        return data
    if data['method'] == 'recompute_rpn_cache_values':
        for k in data['cache']:
            value, error = parse_rpn_value(k, data['variables'])
            if not error:
                data['cache'][k] = value
        return data
    raise RuntimeError('unknown application data method: {}'.format(data['method']))


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
        path = str(run_dir.join(ELEGANT_LOG_FILE))
        with open(path) as f:
            return 'elegant-output.txt', f.read(), 'text/plain'

    if model == 'beamlineReport':
        data = simulation_db.read_json(str(run_dir.join('..', simulation_db.SIMULATION_DATA_FILE)))
        source = generate_parameters_file(data, _SCHEMA, is_parallel=True)
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


def is_rpn_value(value):
    if (value):
        if re.search(r'^\s*(\-|\+)?(\d+|(\d*(\.\d*)))([eE][+-]?\d+)?\s*$', str(value)):
            return False
        return True
    return False


def models_related_to_report(data):
    r = data['report']
    if not 'bunchReport' in r:
        return []
    return ['bunch', 'simulation', 'bunchSource', 'bunchFile']


def new_simulation(data, new_simulation_data):
    pass


def parse_rpn_value(value, variable_list):
    variables = {x['name']: x['value'] for x in variable_list}
    my_env = os.environ.copy()
    my_env["RPN_DEFNS"] = _RPN_DEFN_FILE
    depends = _build_variable_dependency(value, variables, [])
    var_list = ' '.join(map(lambda x: '{} sto {}'.format(variables[x], x), depends))
    #TODO(pjm): security - need to scrub field value
    out = ''
    try:
        with open(os.devnull, 'w') as devnull:
            pkdc('rpnl "{}" "{}"'.format(var_list, value))
            out = subprocess.check_output(['rpnl', '{} {}'.format(var_list, value)], env=my_env, stderr=devnull)
    except subprocess.CalledProcessError as e:
        return None, 'invalid'
    if len(out):
        return float(out.strip()), None
    return None, 'empty'


def prepare_aux_files(run_dir, data):
    pass


def prepare_for_client(data):
    if 'models' not in data:
        return data
    # evaluate rpn values into model.rpnCache
    cache = {}
    data['models']['rpnCache'] = cache
    state = {
        'cache': cache,
        'rpnVariables': data['models']['rpnVariables'],
    }
    _iterate_model_fields(data, state, _iterator_rpn_values)

    for rpn_var in data['models']['rpnVariables']:
        v, err = parse_rpn_value(rpn_var['value'], data['models']['rpnVariables'])
        if not err:
            cache[rpn_var['name']] = v
            if is_rpn_value(rpn_var['value']):
                cache[rpn_var['value']] = v
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


def write_parameters(data, schema, run_dir, is_parallel):
    """Write the parameters file

    Args:
        data (dict): input
        schema (dict): to validate data
        run_dir (py.path): where to write
        is_parallel (bool): run in background?
    """
    pkio.write_text(
        run_dir.join(template_common.PARAMETERS_PYTHON_FILE),
        generate_parameters_file(
            data,
            schema,
            run_dir,
            is_parallel,
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


def _build_beamline_map(data):
    res = {}
    for bl in data['models']['beamlines']:
        res[bl['id']] = bl['name']
    return res


def _build_filename_map(data):
    res = {
        'keys_in_order': [],
    }
    model_index = {}
    for model_type in ['commands', 'elements']:
        for model in data['models'][model_type]:
            field_index = 0
            model_name = _model_name_for_data(model)
            if model_name in model_index:
                model_index[model_name] += 1
            else:
                model_index[model_name] = 1
            model_schema = _SCHEMA['model'][model_name]
            for k in sorted(model):
                if k not in model_schema:
                    continue
                element_schema = model_schema[k]
                field_index += 1
                if element_schema[1] == 'OutputFile':
                    if model_type == 'elements':
                        filename = '{}.{}.sdds'.format(model['name'], k)
                    else:
                        suffix = 'lte' if model['_type'] == 'save_lattice' else 'sdds';
                        filename = '{}{}.{}.{}'.format(model['_type'], model_index[model_name] if model_index[model_name] > 1 else '', k, suffix)
                    k = '{}-{}'.format(model['_id'], field_index)
                    res[k] = filename
                    res['keys_in_order'].append(k)
    return res


def _build_variable_dependency(value, variables, depends):
    for v in str(value).split(' '):
        if v in variables:
            if v not in depends:
                _build_variable_dependency(variables[v], variables, depends)
                depends.append(v)
    return depends


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


def _create_command(model_name, data):
    model_schema = _SCHEMA['model'][model_name]
    for k in model_schema:
        if k not in data:
            data[k] = model_schema[k][2]
    return data


def _create_default_commands(data):
    max_id = 1
    for model_type in ['elements', 'beamlines']:
        for m in data['models'][model_type]:
            id = m['_id'] if '_id' in m else m['id']
            if id > max_id:
                max_id = id
    simulation = data['models']['simulation']
    bunch = data['models']['bunch']
    return [
        _create_command('command_run_setup', {
            "_id": max_id + 1,
            "_type": "run_setup",
            "centroid": "1",
            "concat_order": 2,
            "lattice": "Lattice",
            "output": "1",
            "p_central_mev": bunch['p_central_mev'],
            "parameters": "1",
            "print_statistics": 1,
            "sigma": "1",
            "use_beamline": simulation['visualizationBeamlineId'] if 'visualizationBeamlineId' in simulation else '',
        }),
        _create_command('command_run_control', {
            "_id": max_id + 2,
            "_type": "run_control",
        }),
        _create_command('command_twiss_output', {
            "_id": max_id + 3,
            "_type": "twiss_output",
            "alpha_x": bunch['alpha_x'],
            "alpha_y": bunch['alpha_y'],
            "beta_x": bunch['beta_x'],
            "beta_y": bunch['beta_y'],
            "filename": "1",
            "matched": "0",
            "output_at_each_step": "1",
            "statistics": 1
        }),
        _create_command('command_bunched_beam', {
            "_id": max_id + 4,
            "_type": "bunched_beam",
            "alpha_x": bunch['alpha_x'],
            "alpha_y": bunch['alpha_y'],
            "alpha_z": bunch['alpha_z'],
            "beta_x": bunch['beta_x'],
            "beta_y": bunch['beta_y'],
            "beta_z": bunch['beta_z'],
            "distribution_cutoff": '3, 3, 3',
            "enforce_rms_values": '1, 1, 1',
            "emit_x": bunch['emit_x'] / 1e09,
            "emit_y": bunch['emit_y'] / 1e09,
            "emit_z": bunch['emit_z'],
            "n_particles_per_bunch": bunch['n_particles_per_bunch'],
            "one_random_bunch": '0',
            "sigma_dp": bunch['sigma_dp'],
            "sigma_s": bunch['sigma_s'] / 1e06,
            "symmetrize": 1,
        }),
        _create_command('command_track', {
            "_id": max_id + 5,
            "_type": "track",
        }),
    ]


def _field_label(field):
    if field in _FIELD_LABEL:
        return _FIELD_LABEL[field]
    return field


def _file_info(filename, run_dir, id, output_index):
    file_path = run_dir.join(filename)
    if not re.search(r'.sdds$', filename, re.IGNORECASE):
        if file_path.exists():
            return {
                'isAuxFile': True,
                'filename': filename,
                'id': '{}-{}'.format(id, output_index),
                'lastUpdateTime': int(os.path.getmtime(str(file_path))),
            }
        return None
    if sdds.sddsdata.InitializeInput(_SDDS_INDEX, str(file_path)) != 1:
        sdds.sddsdata.Terminate(_SDDS_INDEX)
        return None
    column_names = sdds.sddsdata.GetColumnNames(_SDDS_INDEX)
    plottable_columns = []
    double_column_count = 0
    for col in column_names:
        col_type = sdds.sddsdata.GetColumnDefinition(_SDDS_INDEX, col)[4]
        if col_type < _SDDS_STRING_TYPE:
            plottable_columns.append(col)
        if col_type == _SDDS_DOUBLE_TYPE:
            double_column_count += 1
    page_count = 1
    page = sdds.sddsdata.ReadPage(_SDDS_INDEX)
    while page > 0:
        page = sdds.sddsdata.ReadPage(_SDDS_INDEX)
        if page > 0:
            page_count += 1
    sdds.sddsdata.Terminate(_SDDS_INDEX)
    return {
        'isAuxFile': False if double_column_count > 1 else True,
        'filename': filename,
        'id': '{}-{}'.format(id, output_index),
        'pageCount': page_count,
        'columns': column_names,
        'plottableColumns': plottable_columns,
        'lastUpdateTime': int(os.path.getmtime(str(file_path))),
    }


def _generate_commands(data, filename_map, beamline_map, v):
    state = {
        'commands': '',
        'filename_map': filename_map,
        'beamline_map': beamline_map,
    }
    _iterate_model_fields(data, state, _iterator_commands)
    state['commands'] += '&end' + "\n"
    return state['commands']


def _generate_variable(name, variables, visited):
    res = ''
    if name not in visited:
        res += "% " + '{} sto {}'.format(variables[name], name) + "\n"
        visited[name] = True
    return res


def _generate_variables(data):
    res = ''
    visited = {}
    variables = {x['name']: x['value'] for x in data['models']['rpnVariables']}

    for name in sorted(variables):
        for dependency in _build_variable_dependency(variables[name], variables, []):
            res += _generate_variable(dependency, variables, visited)
        res += _generate_variable(name, variables, visited)
    return res


def _get_filename_for_element_id(id, data):
    return _build_filename_map(data)['{}-{}'.format(id[0], id[1])]


#TODO(pjm): keep in sync with elegant.js reportTypeForColumns()
def _is_2d_plot(columns):
    if ('x' in columns and 'xp' in columns) \
       or ('y' in columns and 'yp' in columns) \
       or ('t' in columns and 'p' in columns):
        return False
    return True


def _is_error_text(text):
    return re.search(r'^warn|^error|wrong units|^fatal error|no expansion for entity|unable to find|warning\:|^0 particles left|^unknown token|^terminated by sig|no such file or directory|Unable to compute dispersion|no parameter name found', text, re.IGNORECASE)


def _iterate_model_fields(data, state, callback):
    for model_type in ['commands', 'elements']:
        for m in data['models'][model_type]:
            model_schema = _SCHEMA['model'][_model_name_for_data(m)]
            callback(state, m)

            for k in sorted(m):
                if k not in model_schema:
                    continue
                element_schema = model_schema[k]
                callback(state, m, element_schema, k)


def _iterator_commands(state, model, element_schema=None, field_name=None):
    # only interated in commands, not elements
    if '_type' not in model:
        return
    if element_schema:
        state['field_index'] += 1
        value = model[field_name]
        default_value = element_schema[2]
        if value is not None and default_value is not None:
            if str(value) != str(default_value):
                if element_schema[1] == 'RPNValue' and is_rpn_value(value):
                    state['commands'] += '  {} = "({})",'.format(field_name, value) + "\n"
                elif element_schema[1] == 'StringArray':
                    state['commands'] += '  {}[0] = {},'.format(field_name, value) + "\n"
                else:
                    #TODO(pjm): combine with lattice file input formatting below
                    if element_schema[1] == 'OutputFile':
                        value = state['filename_map']['{}-{}'.format(model['_id'], state['field_index'])]
                    elif element_schema[1].startswith('InputFile'):
                        value = 'command_{}-{}.{}'.format(model['_type'], field_name, value)
                    elif element_schema[1] == 'BeamInputFile':
                        value = 'bunchFile-sourceFile.{}'.format(value)
                    elif element_schema[1] == 'ElegantBeamlineList':
                        value = state['beamline_map'][int(value)]
                    elif element_schema[1] == 'ElegantLatticeList':
                        if value and value == 'Lattice':
                            value = 'elegant.lte'
                        else:
                            value = value + '.filename.lte'
                    state['commands'] += '  {} = "{}",'.format(field_name, value) + "\n"
    else:
        state['field_index'] = 0
        if state['commands']:
            state['commands'] += '&end' + "\n"
        state['commands'] += "\n" + '&{}'.format(model['_type']) + "\n"
        if model['_type'] == 'run_setup':
            state['commands'] += '  semaphore_file = {},'.format(_ELEGANT_SEMAPHORE_FILE) + "\n"


def _iterator_input_files(state, model, element_schema=None, field_name=None):
    if element_schema:
        if model[field_name] and element_schema[1].startswith('InputFile'):
            state.append('{}-{}.{}'.format(_model_name_for_data(model), field_name, model[field_name]))


def _iterator_lattice_elements(state, model, element_schema=None, field_name=None):
    # only interested in elements, not commands
    if 'type' not in model:
        return
    if element_schema:
        state['field_index'] += 1
        if field_name in ['name', 'type', '_id'] or re.search('(X|Y)$', field_name):
            return
        value = model[field_name]
        default_value = element_schema[2]
        if value is not None and default_value is not None:
            if str(value) != str(default_value):
                if element_schema[1].startswith('InputFile'):
                    value = '{}-{}.{}'.format(model['type'], field_name, value)
                    if element_schema[1] == 'InputFileXY':
                        value += '={}+{}'.format(model[field_name + 'X'], model[field_name + 'Y'])
                elif element_schema[1] == 'OutputFile':
                    value = state['filename_map']['{}-{}'.format(model['_id'], state['field_index'])]
                state['lattice'] += '{}="{}",'.format(field_name, value)
    else:
        state['field_index'] = 0
        if state['lattice']:
            state['lattice'] = state['lattice'][:-1]
            state['lattice'] += "\n"
        state['lattice'] += '"{}": {},'.format(model['name'].upper(), model['type'])
        state['beamline_map'][model['_id']] = model['name']


def _iterator_rpn_values(state, model, element_schema=None, field_name=None):
    if element_schema:
        if element_schema[1] == 'RPNValue' and is_rpn_value(model[field_name]):
            v, err = parse_rpn_value(model[field_name], state['rpnVariables'])
            if not err:
                state['cache'][model[field_name]] = v


def _model_name_for_data(model):
    return 'command_{}'.format(model['_type']) if '_type' in model else model['type']


def _output_info(run_dir, data, schema):
    res = []
    filename_map = _build_filename_map(data)
    for k in filename_map['keys_in_order']:
        filename = filename_map[k]
        id = k.split('-')
        info = _file_info(filename, run_dir, id[0], id[1])
        if info:
            res.append(info)
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


def _sdds_error(error_text='invalid data file'):
    sdds.sddsdata.Terminate(_SDDS_INDEX)
    return {
        'error': error_text,
    }


def _validate_data(data, schema):
    # ensure enums match, convert ints/floats, apply scaling
    enum_info = template_common.parse_enums(schema['enum'])
    for k in data['models']:
        if k in schema['model']:
            template_common.validate_model(data['models'][k], schema['model'][k], enum_info)
    for model_type in ['elements', 'commands']:
        for m in data['models'][model_type]:
            template_common.validate_model(m, schema['model'][_model_name_for_data(m)], enum_info)


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
