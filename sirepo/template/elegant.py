# -*- coding: utf-8 -*-
u"""elegant execution template.

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkio
from pykern import pkresource
from pykern.pkdebug import pkdp, pkdc, pkdlog
from sirepo import simulation_db
from sirepo.template import elegant_command_importer
from sirepo.template import elegant_common
from sirepo.template import elegant_lattice_importer
from sirepo.template import template_common, sdds_util
import ast
import glob
import math
import numpy as np
import os
import os.path
import py.path
import re
import sdds
import stat
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
    'LinearDensity': 'Linear Density (C/s)',
    'LinearDensityDeriv': 'LinearDensityDeriv (C/s²)',
    'GammaDeriv': 'GammaDeriv (1/m)',
}

#
_FILE_ID_SEP = '-'

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

_OUTPUT_INFO_FILE = 'outputInfo.json'

_OUTPUT_INFO_VERSION = '2'

_PLOT_TITLE = {
    'x-xp': 'Horizontal',
    'y-yp': 'Vertical',
    'x-y': 'Cross-section',
    't-p': 'Longitudinal',
}

_SDDS_INDEX = 0

_SDDS_Singleton = sdds.SDDS(_SDDS_INDEX)

x = getattr(_SDDS_Singleton, 'SDDS_LONGDOUBLE', None)
_SDDS_DOUBLE_TYPES = [
    _SDDS_Singleton.SDDS_DOUBLE,
    _SDDS_Singleton.SDDS_FLOAT,
]
if x is not None:
    _SDDS_DOUBLE_TYPES.append(x)

_SDDS_STRING_TYPE = _SDDS_Singleton.SDDS_STRING

_SCHEMA = simulation_db.get_schema(elegant_common.SIM_TYPE)

_SIMPLE_UNITS = ['m', 's', 'C', 'rad', 'eV']

_X_FIELD = 's'


def background_percent_complete(report, run_dir, is_running):
    #TODO(robnagler) remove duplication in run_dir.exists() (outer level?)
    errors, last_element = parse_elegant_log(run_dir)
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
    output_info = _output_info(run_dir)
    return {
        'percentComplete': 100,
        'frameCount': 1,
        'outputInfo': output_info,
        'lastUpdateTime': output_info[0]['lastUpdateTime'],
        'errors': errors,
    }


def copy_related_files(data, source_path, target_path):
    # copy any simulation output
    if os.path.isdir(str(py.path.local(source_path).join(get_animation_name(data)))):
        animation_dir = py.path.local(target_path).join(get_animation_name(data))
        pkio.mkdir_parent(str(animation_dir))
        for f in glob.glob(str(py.path.local(source_path).join(get_animation_name(data), '*'))):
            py.path.local(f).copy(animation_dir)


def extract_report_data(xFilename, data, page_index, page_count=0):
    xfield = data['x'] if 'x' in data else data[_X_FIELD]
    # x, column_names, x_def, err
    x_col = sdds_util.extract_sdds_column(xFilename, xfield, page_index)
    if x_col['err']:
        return x_col['err']
    x = x_col['values']
    if not _is_histogram_file(xFilename, x_col['column_names']):
        # parameter plot
        plots = []
        filename = {
            'y1': xFilename,
            #TODO(pjm): y2Filename, y3Filename are not currently used. Would require rescaling x value across files.
            'y2': xFilename,
            'y3': xFilename,
        }
        for f in ('y1', 'y2', 'y3'):
            if re.search(r'^none$', data[f], re.IGNORECASE) or data[f] == ' ':
                continue
            yfield = data[f]
            y_col = sdds_util.extract_sdds_column(filename[f], yfield, page_index)
            if y_col['err']:
                return y_col['err']
            y = y_col['values']
            plots.append({
                'field': yfield,
                'points': y,
                'label': _field_label(yfield, y_col['column_def'][1]),
            })
        title = ''
        if page_count > 1:
            title = 'Plot {} of {}'.format(page_index + 1, page_count)
        return template_common.parameter_plot(x, plots, data, {
            'title': title,
            'y_label': '',
            'x_label': _field_label(xfield, x_col['column_def'][1]),
        })
    yfield = data['y1'] if 'y1' in data else data['y']
    y_col = sdds_util.extract_sdds_column(xFilename, yfield, page_index)
    if y_col['err']:
        return y_col['err']
    return template_common.heatmap([x, y_col['values']], data, {
        'x_label': _field_label(xfield, x_col['column_def'][1]),
        'y_label': _field_label(yfield, y_col['column_def'][1]),
        'title': _plot_title(xfield, yfield, page_index, page_count),
    })


def fixup_old_data(data):
    for m in [
            'bunchSource',
            'twissReport',
    ]:
        if m not in data['models']:
            data['models'][m] = {}
        template_common.update_model_defaults(data['models'][m], m, _SCHEMA)
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
        if m['type'] == 'WATCH':
            m['filename'] = '1'
            if m['mode'] == 'coordinates' or m['mode'] == 'coord':
                m['mode'] = 'coordinate'
        template_common.update_model_defaults(m, m['type'], _SCHEMA)
    if 'centroid' not in data['models']['bunch']:
        bunch = data['models']['bunch']
        for f in ('emit_x', 'emit_y', 'emit_z'):
            if bunch[f] and not isinstance(bunch[f], basestring):
                bunch[f] /= 1e9
        if bunch['sigma_s'] and not isinstance(bunch['sigma_s'], basestring):
            bunch['sigma_s'] /= 1e6
        first_bunch_command = _find_first_bunch_command(data)
        # first_bunch_command may not exist if the elegant sim has no bunched_beam command
        if first_bunch_command:
            first_bunch_command['symmetrize'] = str(first_bunch_command['symmetrize'])
            for f in _SCHEMA['model']['bunch']:
                if f not in bunch and f in first_bunch_command:
                    bunch[f] = first_bunch_command[f]
        else:
            bunch['centroid'] = '0,0,0,0,0,0'
    for m in data['models']['commands']:
        template_common.update_model_defaults(m, 'command_{}'.format(m['_type']), _SCHEMA)
    template_common.organize_example(data)


def generate_lattice(data, filename_map, beamline_map, v):
    beamlines = {}

    selected_beamline_id = 0
    sim = data['models']['simulation']
    if 'visualizationBeamlineId' in sim and sim['visualizationBeamlineId']:
        selected_beamline_id = int(sim['visualizationBeamlineId'])
    elif len(data['models']['beamlines']):
        selected_beamline_id = data['models']['beamlines'][0]['id']

    for bl in data['models']['beamlines']:
        if selected_beamline_id == int(bl['id']):
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
    res, v = template_common.generate_parameters_file(data)
    v['rpn_variables'] = _generate_variables(data)

    if is_parallel:
        return res + _generate_full_simulation(data, v)

    if 'report' in data and data['report'] == 'twissReport':
        return res + _generate_twiss_simulation(data, v)

    return res + _generate_bunch_simulation(data, v)


def get_animation_name(data):
    return 'animation'


def get_application_data(data):
    if data['method'] == 'get_beam_input_type':
        if data['input_file']:
            data['input_type'] = _sdds_beam_type_from_file(data['input_file'])
        return data
    if data['method'] == 'rpn_value':
        value, error = _parse_expr(data['value'], _variables_to_postfix(data['variables']))
        if error:
            data['error'] = error
        else:
            data['result'] = value
        return data
    if data['method'] == 'recompute_rpn_cache_values':
        variables = _variables_to_postfix(data['variables'])
        for k in data['cache']:
            value, error = _parse_expr(k, variables)
            if not error:
                data['cache'][k] = value
        return data
    raise RuntimeError('unknown application data method: {}'.format(data['method']))


def _file_name_from_id(file_id, model_data, run_dir):
    return str(run_dir.join(
        _get_filename_for_element_id(file_id.split(_FILE_ID_SEP), model_data)))


def get_simulation_frame(run_dir, data, model_data):
    frame_index = int(data['frameIndex'])
    frame_data = template_common.parse_animation_args(
        data,
        {
            '1': ['x', 'y', 'histogramBins', 'xFileId', 'startTime'],
            '2': ['x', 'y', 'histogramBins', 'xFileId', 'yFileId', 'startTime'],
            '3': ['x', 'y1', 'y2', 'y3', 'histogramBins', 'xFileId', 'y2FileId', 'y3FileId', 'startTime'],
            '4': ['x', 'y1', 'y2', 'y3', 'histogramBins', 'xFileId', 'startTime'],
            '': ['x', 'y1', 'y2', 'y3', 'histogramBins', 'xFileId', 'plotRangeType', 'horizontalSize', 'horizontalOffset', 'verticalSize', 'verticalOffset', 'startTime'],
        },
    )
    page_count = 0
    for info in _output_info(run_dir):
        if info['modelKey'] == data['modelName']:
            page_count = info['pageCount']
            frame_data['fieldRange'] = info['fieldRange']
    frame_data['y'] = frame_data['y1']
    return extract_report_data(
        _file_name_from_id(frame_data.xFileId, model_data, run_dir),
        frame_data,
        frame_index,
        page_count=page_count,
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

    if model == get_animation_name(None):
        path = run_dir.join(ELEGANT_LOG_FILE)
        if not path.exists():
            return 'elegant-output.txt', '', 'text/plain'
        with open(str(path)) as f:
            return 'elegant-output.txt', f.read(), 'text/plain'

    if model == 'beamlineReport':
        data = simulation_db.read_json(str(run_dir.join('..', simulation_db.SIMULATION_DATA_FILE)))
        source = generate_parameters_file(data, is_parallel=True)
        return 'python-source.py', source, 'text/plain'

    return _sdds(_report_output_filename('bunchReport'))


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
    data['models']['simulation']['name'] = re.sub(r'\.(lte|ele)$', '', filename, flags=re.IGNORECASE)
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
    return template_common.filename_to_path(_simulation_files(data), source_lib)


def models_related_to_report(data):
    """What models are required for this data['report']

    Args:
        data (dict): simulation
    Returns:
        list: Named models, model fields or values (dict, list) that affect report
    """
    r = data['report']
    res = []
    if r == 'twissReport' or 'bunchReport' in r:
        res = ['bunch', 'bunchSource', 'bunchFile']
        for f in template_common.lib_files(data):
            if f.exists():
                res.append(f.mtime())
    if r == 'twissReport':
        res += ['elements', 'beamlines', 'commands', 'simulation.activeBeamlineId']
    return res


def parse_elegant_log(run_dir):
    path = run_dir.join(ELEGANT_LOG_FILE)
    if not path.exists():
        return '', 0
    res = ''
    last_element = None
    text = pkio.read_text(str(path))
    want_next_line = False
    prev_line = ''
    prev_err = ''
    for line in text.split("\n"):
        if line == prev_line:
            continue
        match = re.search('^Starting (\S+) at s\=', line)
        if match:
            name = match.group(1)
            if not re.search('^M\d+\#', name):
                last_element = name
        if want_next_line:
            res += line + "\n"
            want_next_line = False
        elif _is_ignore_error_text(line):
            pass
        elif _is_error_text(line):
            if len(line) < 10:
                want_next_line = True
            else:
                if line != prev_err:
                    res += line + "\n"
                prev_err = line
        prev_line = line
    return res, last_element


def prepare_for_client(data):
    if 'models' not in data:
        return data
    # evaluate rpn values into model.rpnCache
    cache = {}
    data['models']['rpnCache'] = cache
    variables = _variables_to_postfix(data['models']['rpnVariables'])
    state = {
        'cache': cache,
        'rpnVariables': variables,
    }
    _iterate_model_fields(data, state, _iterator_rpn_values)

    for rpn_var in data['models']['rpnVariables']:
        v, err = _parse_expr(rpn_var['value'], variables)
        if not err:
            cache[rpn_var['name']] = v
            if elegant_lattice_importer.is_rpn_value(rpn_var['value']):
                cache[rpn_var['value']] = v
    return data


def prepare_output_file(run_dir, data):
    if data['report'] == 'twissReport' or 'bunchReport' in data['report']:
        fn = simulation_db.json_filename(template_common.OUTPUT_BASE_NAME, run_dir)
        if fn.exists():
            fn.remove()
            output_file = run_dir.join(_report_output_filename(data['report']))
            if output_file.exists():
                save_report_data(data, run_dir)


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


def save_report_data(data, run_dir):
    report = data['models'][data['report']]
    if data['report'] == 'twissReport':
        report['x'] = 's'
        report['y'] = report['y1']
    simulation_db.write_result(
        extract_report_data(str(run_dir.join(_report_output_filename(data['report']))), report, 0),
        run_dir=run_dir,
    )


def simulation_dir_name(report_name):
    if 'bunchReport' in report_name:
        return 'bunchReport'
    return report_name


def validate_delete_file(data, filename, file_type):
    """Returns True if the filename is in use by the simulation data."""
    return filename in _simulation_files(data)


def validate_file(file_type, path):
    err = None
    if file_type == 'bunchFile-sourceFile':
        err = 'expecting sdds file with (x, xp, y, yp, t, p) or (r, pr, pz, t, pphi) columns'
        if sdds.sddsdata.InitializeInput(_SDDS_INDEX, path) == 1:
            beam_type = _sdds_beam_type(sdds.sddsdata.GetColumnNames(_SDDS_INDEX))
            if beam_type in ('elegant', 'spiffe'):
                sdds.sddsdata.ReadPage(_SDDS_INDEX)
                if len(sdds.sddsdata.GetColumn(_SDDS_INDEX, 0)) > 0:
                    err = None
                else:
                    err = 'sdds file contains no rows'
        sdds.sddsdata.Terminate(_SDDS_INDEX)
    return err


def write_parameters(data, run_dir, is_parallel):
    """Write the parameters file

    Args:
        data (dict): input
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
    for f in _simulation_files(data):
        if re.search(r'SCRIPT-commandFile', f):
            os.chmod(str(run_dir.join(f)), stat.S_IRUSR | stat.S_IXUSR)


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
                        suffix = _command_file_extension(model)
                        filename = '{}{}.{}.{}'.format(model['_type'], model_index[model_name] if model_index[model_name] > 1 else '', k, suffix)
                    k = '{}{}{}'.format(model['_id'], _FILE_ID_SEP, field_index)
                    res[k] = filename
                    res['keys_in_order'].append(k)
    return res


def _command_file_extension(model):
    if model['_type'] == 'save_lattice':
        return 'lte'
    if model['_type'] == 'global_settings':
        return 'txt'
    return 'sdds'


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


def _contains_columns(column_names, search):
    for col in search:
        if col not in column_names:
            return False
    return True


def _correct_halo_gaussian_distribution_type(m):
    # the halo(gaussian) value will get validated/escaped to halogaussian, change it back
    if 'distribution_type' in m and 'halogaussian' in m['distribution_type']:
        m['distribution_type'] = m['distribution_type'].replace("halogaussian", 'halo(gaussian)')


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
            "print_statistics": "1",
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
            "filename": "1",
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
            "symmetrize": '1',
            "Po": 0.0,
        }),
        _create_command('command_track', {
            "_id": max_id + 5,
            "_type": "track",
        }),
    ]

def _field_label(field, units):
    if field in _FIELD_LABEL:
        return _FIELD_LABEL[field]
    if units in _SIMPLE_UNITS:
        return '{} [{}]'.format(field, units)
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
        field_range = {}
        for col in column_names:
            col_type = sdds.sddsdata.GetColumnDefinition(_SDDS_INDEX, col)[4]
            if col_type < _SDDS_STRING_TYPE:
                plottable_columns.append(col)
            if col_type in _SDDS_DOUBLE_TYPES:
                double_column_count += 1
            field_range[col] = []
        parameter_names = sdds.sddsdata.GetParameterNames(_SDDS_INDEX)
        parameters = dict([(p, []) for p in parameter_names])
        page_count = 0
        row_counts = []
        while True:
            if sdds.sddsdata.ReadPage(_SDDS_INDEX) <= 0:
                break
            row_counts.append(sdds.sddsdata.RowCount(_SDDS_INDEX))
            page_count += 1
            for i, p in enumerate(parameter_names):
                parameters[p].append(_safe_sdds_value(sdds.sddsdata.GetParameter(_SDDS_INDEX, i)))
            for col in column_names:
                values = sdds.sddsdata.GetColumn(
                    _SDDS_INDEX,
                    column_names.index(col),
                )
                if not len(values):
                    pass
                elif len(field_range[col]):
                    field_range[col][0] = min(_safe_sdds_value(min(values)), field_range[col][0])
                    field_range[col][1] = max(_safe_sdds_value(max(values)), field_range[col][1])
                else:
                    field_range[col] = [_safe_sdds_value(min(values)), _safe_sdds_value(max(values))]
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
            'isHistogram': _is_histogram_file(filename, column_names),
            'fieldRange': field_range,
        }
    finally:
        try:
            sdds.sddsdata.Terminate(_SDDS_INDEX)
        except Exception:
            pass


def _find_first_command(data, command_type):
    for m in data['models']['commands']:
        if m['_type'] == command_type:
            return m
    return None


def _find_first_bunch_command(data):
    return _find_first_command(data, 'bunched_beam')


def _format_rpn_value(value, is_command=False):
    if elegant_lattice_importer.is_rpn_value(value):
        value = _infix_to_postfix(value)
        if is_command:
            return '({})'.format(value)
    return value


def _generate_bunch_simulation(data, v):
    for f in _SCHEMA['model']['bunch']:
        info = _SCHEMA['model']['bunch'][f]
        if info[1] == 'RPNValue':
            field = 'bunch_{}'.format(f)
            v[field] = _format_rpn_value(v[field], is_command=True)
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
        if v['bunchFile_sourceFile'] and v['bunchFile_sourceFile'] != 'None':
            v['bunchInputFile'] = template_common.lib_file_name('bunchFile', 'sourceFile', v['bunchFile_sourceFile'])
            v['bunchFileType'] = _sdds_beam_type_from_file(v['bunchInputFile'])
    v['bunchOutputFile'] = _report_output_filename('bunchReport')
    return template_common.render_jinja(SIM_TYPE, v, 'bunch.py')


def _generate_commands(data, filename_map, beamline_map, v):
    state = {
        'commands': '',
        'filename_map': filename_map,
        'beamline_map': beamline_map,
    }
    _iterate_model_fields(data, state, _iterator_commands)
    state['commands'] += '&end' + "\n"
    return state['commands']


def _generate_full_simulation(data, v):
    filename_map = _build_filename_map(data)
    beamline_map = _build_beamline_map(data)
    v['commands'] = _generate_commands(data, filename_map, beamline_map, v)
    v['lattice'] = generate_lattice(data, filename_map, beamline_map, v)
    v['simulationMode'] = data['models']['simulation']['simulationMode']
    return template_common.render_jinja(SIM_TYPE, v)


def _generate_twiss_simulation(data, v):
    max_id = elegant_lattice_importer.max_id(data)
    sim = data['models']['simulation']
    sim['simulationMode'] = 'serial'
    run_setup = _find_first_command(data, 'run_setup') or {
        '_id': max_id + 1,
        '_type': 'run_setup',
        'lattice': 'Lattice',
        'p_central_mev': data['models']['bunch']['p_central_mev'],
    }
    run_setup['use_beamline'] = sim['activeBeamlineId']
    twiss_output = _find_first_command(data, 'twiss_output') or {
        '_id': max_id + 2,
        '_type': 'twiss_output',
        'filename': '1',
    }
    twiss_output['final_values_only'] = '0'
    twiss_output['output_at_each_step'] = '0'
    data['models']['commands'] = [
        run_setup,
        twiss_output,
    ]
    filename_map = _build_filename_map(data)
    beamline_map = _build_beamline_map(data)
    v['lattice'] = generate_lattice(data, filename_map, beamline_map, v)
    v['commands'] = _generate_commands(data, filename_map, beamline_map, v)
    return template_common.render_jinja(SIM_TYPE, v)


def _generate_variable(name, variables, visited):
    res = ''
    if name not in visited:
        res += "% " + '{} sto {}'.format(_format_rpn_value(variables[name]), name) + "\n"
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


def _infix_to_postfix(expr):
    try:
        rpn = _parse_expr_infix(expr)
        #pkdc('{} => {}', expr, rpn)
        expr = rpn
    except Exception as e:
        #pkdc('{}: not infix: {}', expr, e)
        pass
    return expr


def _is_error_text(text):
    return re.search(r'^warn|^error|wrong units|^fatal |no expansion for entity|unable to|warning\:|^0 particles left|^unknown token|^terminated by sig|no such file or directory|no parameter name found|Problem opening |Terminated by SIG|No filename given|^MPI_ERR', text, re.IGNORECASE)


def _is_histogram_file(filename, columns):
    filename = os.path.basename(filename)
    if re.search(r'^closed_orbit.output', filename):
        return False
    if 'xFrequency' in columns and 'yFrequency' in columns:
        return False
    if ('x' in columns and 'xp' in columns) \
       or ('y' in columns and 'yp' in columns) \
       or ('t' in columns and 'p' in columns):
        return True
    return False


def _is_ignore_error_text(text):
    return re.search(r'^warn.* does not have a parameter', text, re.IGNORECASE)


def _is_numeric(el_type, value):
    return el_type in ('RPNValue', 'RPNBoolean', 'Integer', 'Float') \
        and re.search(r'^[\-\+0-9eE\.]+$', str(value))


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
                el_type = element_schema[1]
                if el_type.endswith('StringArray'):
                    state['commands'] += '  {}[0] = {},'.format(field_name, value) + "\n"
                else:
                    #TODO(pjm): combine with lattice file input formatting below
                    if el_type == 'RPNValue':
                        value = _format_rpn_value(value, is_command=True)
                    elif el_type == 'OutputFile':
                        value = state['filename_map']['{}{}{}'.format(model['_id'], _FILE_ID_SEP, state['field_index'])]
                    elif el_type.startswith('InputFile'):
                        value = template_common.lib_file_name('command_{}'.format(model['_type']), field_name, value)
                    elif el_type == 'BeamInputFile':
                        value = 'bunchFile-sourceFile.{}'.format(value)
                    elif el_type == 'LatticeBeamlineList':
                        value = state['beamline_map'][int(value)]
                    elif el_type == 'ElegantLatticeList':
                        if value and value == 'Lattice':
                            value = 'elegant.lte'
                        else:
                            value = value + '.filename.lte'
                    if not _is_numeric(el_type, str(value)):
                        value = '"{}"'.format(value)
                    state['commands'] += '  {} = {},'.format(field_name, value) + "\n"
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
            state.append(template_common.lib_file_name(_model_name_for_data(model), field_name, model[field_name]))


def _iterator_lattice_elements(state, model, element_schema=None, field_name=None):
    # only interested in elements, not commands
    if '_type' in model:
        return
    if element_schema:
        state['field_index'] += 1
        if field_name in ['name', 'type', '_id'] or re.search('(X|Y|File)$', field_name):
            return
        value = model[field_name]
        default_value = element_schema[2]
        if value is not None and default_value is not None:
            if str(value) != str(default_value):
                el_type = element_schema[1]
                if model['type'] == 'SCRIPT' and field_name == 'command':
                    for f in ('commandFile', 'commandInputFile'):
                        if f in model and model[f]:
                            fn = template_common.lib_file_name(model['type'], f, model[f])
                            value = re.sub(r'\b' + re.escape(model[f]) + r'\b', fn, value)
                    if model['commandFile']:
                        value = './' + value
                if el_type == 'RPNValue':
                    value = _format_rpn_value(value)
                if el_type.startswith('InputFile'):
                    value = template_common.lib_file_name(model['type'], field_name, value)
                    if el_type == 'InputFileXY':
                        value += '={}+{}'.format(model[field_name + 'X'], model[field_name + 'Y'])
                elif el_type == 'OutputFile':
                    value = state['filename_map']['{}{}{}'.format(model['_id'], _FILE_ID_SEP, state['field_index'])]
                if not _is_numeric(el_type, value):
                    value = '"{}"'.format(value)
                state['lattice'] += '{}={},'.format(field_name, value)
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
            if model[field_name] not in state['cache']:
                v, err = _parse_expr(model[field_name], state['rpnVariables'])
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


def _output_info(run_dir):
    # cache outputInfo to file, used later for report frames
    info_file = run_dir.join(_OUTPUT_INFO_FILE)
    if os.path.isfile(str(info_file)):
        try:
            res = simulation_db.read_json(info_file)
            if len(res) == 0 or res[0].get('_version', '') == _OUTPUT_INFO_VERSION:
                return res
        except ValueError as e:
            pass
    data = simulation_db.read_json(run_dir.join(template_common.INPUT_BASE_NAME))
    res = []
    filename_map = _build_filename_map(data)
    for k in filename_map['keys_in_order']:
        filename = filename_map[k]
        id = k.split(_FILE_ID_SEP)
        info = _file_info(filename, run_dir, id[0], id[1])
        if info:
            info['modelKey'] = 'elementAnimation{}'.format(info['id'])
            res.append(info)
    if len(res):
        res[0]['_version'] = _OUTPUT_INFO_VERSION
    simulation_db.write_json(info_file, res)
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


def _parse_expr(expr, variables):
    """If not infix, default to rpn"""
    return elegant_lattice_importer.parse_rpn_value(_infix_to_postfix(expr), variables)


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


def _plot_title(xfield, yfield, page_index, page_count):
    key = '{}-{}'.format(xfield, yfield)
    title = ''
    if key in _PLOT_TITLE:
        title = _PLOT_TITLE[key]
    else:
        title = '{} / {}'.format(xfield, yfield)
    if page_count > 1:
        title += ', Plot {} of {}'.format(page_index + 1, page_count)
    return title


def _report_output_filename(report):
    if report == 'twissReport':
        return 'twiss_output.filename.sdds'
    return 'elegant.bun'


def _safe_sdds_value(v):
    if isinstance(v, float) and (math.isinf(v) or math.isnan(v)):
        return 0
    return v


def _sdds_beam_type(column_names):
    if _contains_columns(column_names, ['x', 'xp', 'y', 'yp', 't', 'p']):
        return 'elegant'
    if _contains_columns(column_names, ['r', 'pr', 'pz', 't', 'pphi']):
        return 'spiffe'
    return ''


def _sdds_beam_type_from_file(filename):
    res = ''
    path = str(simulation_db.simulation_lib_dir(SIM_TYPE).join(filename))
    if sdds.sddsdata.InitializeInput(_SDDS_INDEX, path) == 1:
        res = _sdds_beam_type(sdds.sddsdata.GetColumnNames(_SDDS_INDEX))
    sdds.sddsdata.Terminate(_SDDS_INDEX)
    return res


def _simulation_files(data):
    res = []
    _iterate_model_fields(data, res, _iterator_input_files)
    if data['models']['bunchFile']['sourceFile']:
        res.append('{}-{}.{}'.format('bunchFile', 'sourceFile', data['models']['bunchFile']['sourceFile']))
    return res


def _validate_data(data, schema):
    # ensure enums match, convert ints/floats, apply scaling
    enum_info = template_common.validate_models(data, schema)
    _correct_halo_gaussian_distribution_type(data['models']['bunch'])
    for model_type in ['elements', 'commands']:
        for m in data['models'][model_type]:
            template_common.validate_model(m, schema['model'][_model_name_for_data(m)], enum_info)
            _correct_halo_gaussian_distribution_type(m)


def _variables_to_postfix(rpn_variables):
    res = []
    for v in rpn_variables:
        if 'value' not in v:
            pkdlog('rpn var missing value: {}', v['name'])
            v['value'] = '0'
        res.append({
            'name': v['name'],
            'value': _infix_to_postfix(v['value']),
        })
    return res


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
