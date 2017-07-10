# -*- coding: utf-8 -*-
u"""elegant execution template.

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkio
from pykern import pkjinja
from pykern import pkresource
from pykern.pkdebug import pkdp, pkdc, pkdlog
from sirepo import simulation_db
from sirepo.template import elegant_command_importer
from sirepo.template import elegant_common
from sirepo.template import elegant_lattice_importer
from sirepo.template import template_common
import ast
import glob
import numpy as np
import os
import os.path
import py.path
import re
import sdds
import werkzeug

#: Simulation type
ELEGANT_LOG_FILE = 'elegant.log'

SIM_TYPE = elegant_common.SIM_TYPE

WANT_BROWSER_FRAME_CACHE = True

_ELEGANT_SEMAPHORE_FILE = 'run_setup.semaphore'

_FIELD_LABEL = {
    'x': 'x [m]',
    'xp': "x' [rad]",
    'y': 'y [m]',
    'yp': "y' [rad]",
    't': 't [s]',
    'p': 'p (mₑc)',
    's': 's [m]',
    'LinearDensity': 'Linear Density [C/s]',
    'LinearDensityDeriv': 'LinearDensityDeriv [C/s²]',
    'GammaDeriv': 'GammaDeriv [1/m]',
}

#
_FILE_ID_SEP = '-'

_PLOT_TITLE = {
    'x-xp': 'Horizontal',
    'y-yp': 'Vertical',
    'x-y': 'Cross-section',
    't-p': 'Longitudinal',
}

_SDDS_INDEX = 0

_SDDS_DOUBLE_TYPE = 1

_SDDS_STRING_TYPE = 7

_SCHEMA = simulation_db.get_schema(elegant_common.SIM_TYPE)

_INFIX_TO_RPN = {
    ast.Add: '+',
    ast.Div: '/',
    ast.Invert: '!',
    ast.Mult: '*',
    ast.Not: '!',
    ast.Pow: 'pow',
    ast.Sub: '-',
    ast.UAdd: '+',
    ast.USub: '+',
}

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
            py.path.local(f).copy(animation_dir)
    # copy element InputFiles to lib
    #TODO(robnagler) only should copy valid files. Make sure no path names
    template_common.copy_lib_files(
        data,
        py.path.local(os.path.dirname(source_path)).join('lib'),
        py.path.local(os.path.dirname(target_path)).join('lib'),
    )


def extract_report_data(xFilename, yFilename, data, p_central_mev, page_index):
    xfield = data['x']
    yfield = data['y']
    bins = data['histogramBins']

    x, column_names, err = _extract_sdds_column(xFilename, xfield, page_index)
    if err:
        return err
    y, _, err = _extract_sdds_column(yFilename, yfield, page_index)
    if err:
        return err
    if _is_2d_plot(column_names):
        # 2d plot
        return {
            'title': _plot_title(xfield, yfield, page_index),
            'x_range': [np.min(x), np.max(x)],
            'x_label': _field_label(xfield),
            'y_label': _field_label(yfield),
            'points': y,
            'x_points': x,
        }
    hist, edges = np.histogramdd([x, y], template_common.histogram_bins(bins))
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
    if 'simulationMode' not in data['models']['simulation']:
        data['models']['simulation']['simulationMode'] = 'parallel'
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


def generate_parameters_file(data, is_parallel=False):
    _validate_data(data, _SCHEMA)
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
        v['simulationMode'] = data['models']['simulation']['simulationMode']
        return pkjinja.render_resource('elegant.py', v)

    return pkjinja.render_resource('elegant_bunch.py', v)


def get_animation_name(data):
    return 'animation'


def get_application_data(data):
    if data['method'] == 'rpn_value':
        value, error = _parse_expr(data['value'], data['variables'])
        if error:
            data['error'] = error
        else:
            data['result'] = value
        return data
    if data['method'] == 'recompute_rpn_cache_values':
        for k in data['cache']:
            value, error = _parse_expr(k, data['variables'])
            if not error:
                data['cache'][k] = value
        return data
    raise RuntimeError('unknown application data method: {}'.format(data['method']))


def get_simulation_frame(run_dir, data, model_data):
    frame_index = int(data['frameIndex'])
    frame_data = template_common.parse_animation_args(
        data,
        {
            '1': ['x', 'y', 'histogramBins', 'xFileId', 'startTime'],
            '': ['x', 'y', 'histogramBins', 'xFileId', 'yFileId', 'startTime'],
        },
    )
    if frame_data.version <= 1:
        frame_data.yFileId = frame_data.xFileId;
    xFileId = frame_data.xFileId.split(_FILE_ID_SEP)
    yFileId = frame_data.yFileId.split(_FILE_ID_SEP)
    xFilename = _get_filename_for_element_id(xFileId, model_data)
    yFilename = _get_filename_for_element_id(yFileId, model_data)
    return extract_report_data(
        str(run_dir.join(xFilename)),
        str(run_dir.join(yFilename)),
        frame_data,
        model_data['models']['bunch']['p_central_mev'],
        frame_index,
    )


def get_data_file(run_dir, model, frame, options=None):
    def _sdds(filename):
        path = run_dir.join(filename)
        assert path.check(file=True, exists=True), \
            '{}: not found'.format(path)
        if not options.suffix:
            with open(str(path)) as f:
                return path.basename, f.read(), 'application/octet-stream'
        if options.suffix == 'csv':
            out = elegant_common.subprocess_output(['sddsprintout', '-columns', '-spreadsheet=csv', str(path)])
            assert out, \
                '{}: invalid or empty output from sddsprintout'.format(path)
            return path.purebasename + '.csv', out, 'text/csv'
        raise AssertionError('{}: invalid suffix for download path={}'.format(options.suffix, path))

    if frame >= 0:
        data = simulation_db.read_json(run_dir.join(template_common.INPUT_BASE_NAME))
        # ex. elementAnimation17-55
        i = re.sub(r'elementAnimation', '', model).split(_FILE_ID_SEP)
        return _sdds(_get_filename_for_element_id(i, data))

    if model == 'animation':
        path = str(run_dir.join(ELEGANT_LOG_FILE))
        with open(path) as f:
            return 'elegant-output.txt', f.read(), 'text/plain'

    if model == 'beamlineReport':
        data = simulation_db.read_json(str(run_dir.join('..', simulation_db.SIMULATION_DATA_FILE)))
        source = generate_parameters_file(data, is_parallel=True)
        return 'python-source.py', source, 'text/plain'

    return _sdds('elegant.bun')


def import_file(request, lib_dir=None, tmp_dir=None, test_data=None):
    # input_data is passed by test cases only
    f = request.files['file']
    filename = werkzeug.secure_filename(f.filename)
    input_data = test_data

    if 'simulationId' in request.form:
        input_data = simulation_db.read_simulation_json(elegant_common.SIM_TYPE, sid=request.form['simulationId'])
    if re.search(r'.ele$', filename, re.IGNORECASE):
        data = elegant_command_importer.import_file(f.read())
    elif re.search(r'.lte$', filename, re.IGNORECASE):
        data = elegant_lattice_importer.import_file(f.read(), input_data)
        if input_data:
            _map_commands_to_lattice(data)
    else:
        raise IOError('invalid file extension, expecting .ele or .lte')
    data['models']['simulation']['name'] = re.sub(r'\.(lte|ele)$', '', filename, re.IGNORECASE)
    if input_data and not test_data:
        simulation_db.delete_simulation(elegant_common.SIM_TYPE, input_data['models']['simulation']['simulationId'])
    return data


def lib_files(data, source_lib):
    """Returns list of auxiliary files

    Args:
        data (dict): simulation db
        source_lib (py.path): directory of source

    Returns:
        list: py.path.local of source files
    """
    res = []
    _iterate_model_fields(data, res, _iterator_input_files)
    if data['models']['bunchFile']['sourceFile']:
        res.append('{}-{}.{}'.format('bunchFile', 'sourceFile', data['models']['bunchFile']['sourceFile']))
    return template_common.internal_lib_files(res, source_lib)


def models_related_to_report(data):
    """What models are required for this data['report']

    Args:
        data (dict): simulation
    Returns:
        list: Named models, model fields or values (dict, list) that affect report
    """
    r = data['report']
    if 'bunchReport' not in r:
        return []
    return [r, 'bunch', 'bunchSource', 'bunchFile']


def new_simulation(data, new_simulation_data):
    pass


def prepare_aux_files(run_dir, data):
    template_common.copy_lib_files(data, None, run_dir)


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
        v, err = elegant_lattice_importer.parse_rpn_value(rpn_var['value'], data['models']['rpnVariables'])
        if not err:
            cache[rpn_var['name']] = v
            if elegant_lattice_importer.is_rpn_value(rpn_var['value']):
                cache[rpn_var['value']] = v
    return data


def prepare_for_save(data):
    return data


def python_source_for_model(data, model):
    return generate_parameters_file(data, is_parallel=True) + '''
with open('elegant.lte', 'w') as f:
    f.write(lattice_file)

with open('elegant.ele', 'w') as f:
    f.write(elegant_file)

import os
os.system('elegant elegant.ele')
'''


def remove_last_frame(run_dir):
    pass


def resource_files():
    """Library shared between simulations of this type

    Returns:
        list: py.path.local objects
    """
    return pkio.sorted_glob(elegant_common.RESOURCE_DIR.join('*.sdds'))


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


def _ast_dump(node, annotate_fields=True, include_attributes=False, indent='  '):
    """
    Taken from:
    https://bitbucket.org/takluyver/greentreesnakes/src/587ad72894bc7595bc30e33affaa238ac32f0740/astpp.py?at=default&fileviewer=file-view-default

    Return a formatted dump of the tree in *node*.  This is mainly useful for
    debugging purposes.  The returned string will show the names and the values
    for fields.  This makes the code impossible to evaluate, so if evaluation is
    wanted *annotate_fields* must be set to False.  Attributes such as line
    numbers and column offsets are not dumped by default.  If this is wanted,
    *include_attributes* can be set to True.
    """

    def _format(node, level=0):
        if isinstance(node, ast.AST):
            fields = [(a, _format(b, level)) for a, b in ast.iter_fields(node)]
            if include_attributes and node._attributes:
                fields.extend(
                    [(a, _format(getattr(node, a), level))
                     for a in node._attributes],
                )
            return ''.join([
                node.__class__.__name__,
                '(',
                ', '.join(('%s=%s' % field for field in fields)
                           if annotate_fields else
                           (b for a, b in fields)),
                ')',
            ])
        elif isinstance(node, list):
            lines = ['[']
            lines.extend(
                (indent * (level + 2) + _format(x, level + 2) + ','
                 for x in node),
            )
            if len(lines) > 1:
                lines.append(indent * (level + 1) + ']')
            else:
                lines[-1] += ']'
            return '\n'.join(lines)
        return repr(node)

    if not isinstance(node, ast.AST):
        raise TypeError('expected AST, got %r' % node.__class__.__name__)
    return _format(node)


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
                    k = '{}{}{}'.format(model['_id'], _FILE_ID_SEP, field_index)
                    res[k] = filename
                    res['keys_in_order'].append(k)
    return res


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
    max_id = elegant_lattice_importer.max_id(data)
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


def _extract_sdds_column(filename, field, page_index):
    try:
        if sdds.sddsdata.InitializeInput(_SDDS_INDEX, filename) != 1:
            err = _sdds_error('{}: cannot access'.format(filename))
        else:
            column_names = sdds.sddsdata.GetColumnNames(_SDDS_INDEX)
            #TODO(robnagler) SDDS_GotoPage not in sddsdata, why?
            for _ in xrange(page_index + 1):
                if sdds.sddsdata.ReadPage(_SDDS_INDEX) <= 0:
                    #TODO(robnagler) is this an error?
                    break
            try:
                return (
                    sdds.sddsdata.GetColumn(
                        _SDDS_INDEX,
                        column_names.index(field),
                    ),
                    column_names,
                    None,
                )
            except SystemError as e:
                err = _sdds_error(
                    '{}: page not found in {}'.format(page_index, filename))
    finally:
        try:
            sdds.sddsdata.Terminate(_SDDS_INDEX)
        except Exception:
            pass
    return None, None, err


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
                'id': '{}{}{}'.format(id, _FILE_ID_SEP, output_index),
                'lastUpdateTime': int(os.path.getmtime(str(file_path))),
            }
        return None
    try:
        if sdds.sddsdata.InitializeInput(_SDDS_INDEX, str(file_path)) != 1:
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
        parameter_names = sdds.sddsdata.GetParameterNames(_SDDS_INDEX)
        parameters = dict([(p, []) for p in parameter_names])
        page_count = 0
        row_counts = []
        while True:
            page = sdds.sddsdata.ReadPage(_SDDS_INDEX)
            if page <= 0:
                break
            row_counts.append(sdds.sddsdata.RowCount(_SDDS_INDEX))
            page_count += 1
            for i, p in enumerate(parameter_names):
                parameters[p].append(_safe_sdds_value(sdds.sddsdata.GetParameter(_SDDS_INDEX, i)))
        return {
            'isAuxFile': False if double_column_count > 1 else True,
            'filename': filename,
            'id': '{}-{}'.format(id, output_index),
            'rowCounts': row_counts,
            'pageCount': page_count,
            'columns': column_names,
            'parameters': parameters,
            'parameterDefinitions': _parameter_definitions(parameters),
            'plottableColumns': plottable_columns,
            'lastUpdateTime': int(os.path.getmtime(str(file_path))),
        }
    finally:
        try:
            sdds.sddsdata.Terminate(_SDDS_INDEX)
        except Exception:
            pass


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
        for dependency in elegant_lattice_importer.build_variable_dependency(variables[name], variables, []):
            res += _generate_variable(dependency, variables, visited)
        res += _generate_variable(name, variables, visited)
    return res


def _get_filename_for_element_id(id, data):
    return _build_filename_map(data)['{}{}{}'.format(id[0], _FILE_ID_SEP, id[1])]


#TODO(pjm): keep in sync with elegant.js reportTypeForColumns()
def _is_2d_plot(columns):
    if ('x' in columns and 'xp' in columns) \
       or ('y' in columns and 'yp' in columns) \
       or ('t' in columns and 'p' in columns):
        return False
    return True


def _is_error_text(text):
    return re.search(r'^warn|^error|wrong units|^fatal error|no expansion for entity|unable to find|warning\:|^0 particles left|^unknown token|^terminated by sig|no such file or directory|Unable to compute dispersion|no parameter name found|Problem opening |Terminated by SIG', text, re.IGNORECASE)


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
    # only interested in commands, not elements
    if '_type' not in model:
        return
    if element_schema:
        state['field_index'] += 1
        value = model[field_name]
        default_value = element_schema[2]
        if value is not None and default_value is not None:
            if str(value) != str(default_value):
                if element_schema[1] == 'RPNValue' and elegant_lattice_importer.is_rpn_value(value):
                    state['commands'] += '  {} = "({})",'.format(field_name, value) + "\n"
                elif element_schema[1] == 'StringArray':
                    state['commands'] += '  {}[0] = {},'.format(field_name, value) + "\n"
                else:
                    #TODO(pjm): combine with lattice file input formatting below
                    if element_schema[1] == 'OutputFile':
                        value = state['filename_map']['{}{}{}'.format(model['_id'], _FILE_ID_SEP, state['field_index'])]
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
    if '_type' in model:
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
                    value = state['filename_map']['{}{}{}'.format(model['_id'], _FILE_ID_SEP, state['field_index'])]
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
        if element_schema[1] == 'RPNValue' and elegant_lattice_importer.is_rpn_value(model[field_name]):
            v, err = elegant_lattice_importer.parse_rpn_value(model[field_name], state['rpnVariables'])
            if not err:
                state['cache'][model[field_name]] = v


def _map_commands_to_lattice(data):
    for cmd in data['models']['commands']:
        if cmd['_type'] == 'run_setup':
            cmd['lattice'] = 'Lattice'
            break
    for cmd in data['models']['commands']:
        if cmd['_type'] == 'run_setup':
            name = cmd['use_beamline'].upper()
            for bl in data['models']['beamlines']:
                if bl['name'].upper() == name:
                    cmd['use_beamline'] = bl['id']
                    break


def _model_name_for_data(model):
    return 'command_{}'.format(model['_type']) if '_type' in model else model['type']


def _output_info(run_dir, data, schema):
    res = []
    filename_map = _build_filename_map(data)
    for k in filename_map['keys_in_order']:
        filename = filename_map[k]
        id = k.split(_FILE_ID_SEP)
        info = _file_info(filename, run_dir, id[0], id[1])
        if info:
            res.append(info)
    return res


def _parameter_definitions(parameters):
    """Convert parameters to useful definitions"""
    res = {}
    for p in parameters:
        res[p] = dict(zip(
            ['symbol', 'units', 'description', 'format_string', 'type', 'fixed_value'],
            sdds.sddsdata.GetParameterDefinition(_SDDS_INDEX, p),
        ))
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


def _parse_expr(expr, variables):
    """If not infix, default to rpn"""
    try:
        rpn = _parse_expr_infix(expr)
        pkdc('{} => {}', expr, rpn)
        expr = rpn
    except Exception as e:
        pkdc('{}: not infix: {}', expr, e)
    return elegant_lattice_importer.parse_rpn_value(expr, variables)


def _parse_expr_infix(expr):
    """Use Python parser (ast) and return depth first (RPN) tree"""

    # https://bitbucket.org/takluyver/greentreesnakes/src/587ad72894bc7595bc30e33affaa238ac32f0740/astpp.py?at=default&fileviewer=file-view-default

    def _do(n):
        # http://greentreesnakes.readthedocs.io/en/latest/nodes.html
        if isinstance(n, ast.Str):
            assert not re.search('^[^\'"]*$', n.s), \
                '{}: invalid string'.format(n.s)
            return ['"{}"'.format(n.s)]
        elif isinstance(n, ast.Name):
            return [str(n.id)]
        elif isinstance(n, ast.Num):
            return [str(n.n)]
        elif isinstance(n, ast.Expression):
            return _do(n.body)
        elif isinstance(n, ast.Call):
            res = []
            for x in n.args:
                res.extend(_do(x))
            return res + [n.func.id]
        elif isinstance(n, ast.BinOp):
            return _do(n.left) + _do(n.right) + _do(n.op)
        elif isinstance(n, ast.UnaryOp):
            return _do(n.operand) + _do(n.op)
        elif isinstance(n, ast.IfExp):
            return _do(n.test) + ['?'] + _do(n.body) + [':'] + _do(n.orelse) + ['$']
        else:
            x = _INFIX_TO_RPN.get(type(n), None)
            if x:
                return [x]
        raise ValueError('{}: invalid node'._ast_dump(n))

    tree = ast.parse(expr, filename='eval', mode='eval')
    assert isinstance(tree, ast.Expression), \
        "{}: must be an expression".format(tree)
    return ' '.join(_do(tree))


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


def _safe_sdds_value(v):
    if str(v) == 'nan':
        return 0
    return v


def _sdds_error(error_text='invalid data file'):
    sdds.sddsdata.Terminate(_SDDS_INDEX)
    return {
        'error': error_text,
    }


def _validate_data(data, schema):
    # ensure enums match, convert ints/floats, apply scaling
    enum_info = template_common.validate_models(data, schema)
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
