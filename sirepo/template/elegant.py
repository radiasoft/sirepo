# -*- coding: utf-8 -*-
u"""elegant execution template.

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkio
from pykern import pkresource
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
from sirepo import simulation_db
from sirepo.template import elegant_command_importer
from sirepo.template import elegant_common
from sirepo.template import elegant_lattice_importer
from sirepo.template import lattice
from sirepo.template import sdds_util
from sirepo.template import template_common
from sirepo.template.lattice import LatticeUtil
import ast
import copy
import glob
import math
import numpy as np
import os
import os.path
import py.path
import re
import sdds
import sirepo.sim_data
import stat
import werkzeug

_SIM_DATA, SIM_TYPE, _SCHEMA = sirepo.sim_data.template_globals()

ELEGANT_LOG_FILE = 'elegant.log'

WANT_BROWSER_FRAME_CACHE = True

_ELEGANT_SEMAPHORE_FILE = 'run_setup.semaphore'

_FIELD_LABEL = PKDict(
    x='x [m]',
    xp="x' [rad]",
    y='y [m]',
    yp="y' [rad]",
    t='t [s]',
    p='p (mₑc)',
    s='s [m]',
    LinearDensity='Linear Density (C/s)',
    LinearDensityDeriv='LinearDensityDeriv (C/s²)',
    GammaDeriv='GammaDeriv (1/m)',
)

_FILE_ID_SEP = '-'

_INFIX_TO_RPN = PKDict({
    ast.Add: '+',
    ast.Div: '/',
    ast.Invert: '!',
    ast.Mult: '*',
    ast.Not: '!',
    ast.Pow: 'pow',
    ast.Sub: '-',
    ast.UAdd: '+',
    ast.USub: '+',
})

_OUTPUT_INFO_FILE = 'outputInfo.json'

_OUTPUT_INFO_VERSION = '2'

_PLOT_TITLE = PKDict({
    'x-xp': 'Horizontal',
    'y-yp': 'Vertical',
    'x-y': 'Cross-section',
    't-p': 'Longitudinal',
})

_SDDS_INDEX = 0

_s = sdds.SDDS(_SDDS_INDEX)
_x = getattr(_s, 'SDDS_LONGDOUBLE', None)
_SDDS_DOUBLE_TYPES = [_s.SDDS_DOUBLE, _s.SDDS_FLOAT] + ([_x] if _x else [])

_SDDS_STRING_TYPE = _s.SDDS_STRING

_SIMPLE_UNITS = ['m', 's', 'C', 'rad', 'eV']

_X_FIELD = 's'

class CommandIterator(lattice.ElementIterator):
    def start(self, model):
        super(CommandIterator, self).start(model)
        if model._type == 'run_setup':
            self.fields.append(['semaphore_file', _ELEGANT_SEMAPHORE_FILE])

class OutputFileIterator(lattice.ModelIterator):
    def __init__(self):
        self.result = PKDict(
            keys_in_order=[],
        )
        self.model_index = {}

    def field(self, model, field_schema, field):
        self.field_index += 1
        if field_schema[1] == 'OutputFile':
            if LatticeUtil.is_command(model):
                suffix = _command_file_extension(model)
                filename = '{}{}.{}.{}'.format(
                    model._type,
                    self.model_index[self.model_name] if self.model_index[self.model_name] > 1 else '',
                    field,
                    suffix)
            else:
                filename = '{}.{}.sdds'.format(model.name, field)
            k = _file_id(model._id, self.field_index)
            self.result[k] = filename
            self.result.keys_in_order.append(k)

    def start(self, model):
        self.field_index = 0
        self.model_name = LatticeUtil.model_name_for_data(model)
        if self.model_name in self.model_index:
            self.model_index[self.model_name] += 1
        else:
            self.model_index[self.model_name] = 1

class RPNValueIterator(lattice.ModelIterator):
    def __init__(self, rpn_variables):
        self.result = PKDict()
        self.rpn_variables = rpn_variables

    def field(self, model, field_schema, field):
        if field_schema[1] == 'RPNValue' and elegant_lattice_importer.is_rpn_value(model[field]):
            if model[field] not in self.result:
                v, err = _parse_expr(model[field], self.rpn_variables)
                if not err:
                    self.result[model[field]] = v


def background_percent_complete(report, run_dir, is_running):
    #TODO(robnagler) remove duplication in run_dir.exists() (outer level?)
    errors, last_element = parse_elegant_log(run_dir)
    res = PKDict(
        percentComplete=100,
        frameCount=0,
        errors=errors,
    )
    if is_running:
        data = simulation_db.read_json(run_dir.join(template_common.INPUT_BASE_NAME))
        res.percentComplete = _compute_percent_complete(data, last_element)
        return res
    if not run_dir.join(_ELEGANT_SEMAPHORE_FILE).exists():
        return res
    output_info = _output_info(run_dir)
    return PKDict(
        percentComplete=100,
        frameCount=1,
        outputInfo=output_info,
        lastUpdateTime=output_info[0]['lastUpdateTime'],
        errors=errors,
    )


def copy_related_files(data, source_path, target_path):
    # copy any simulation output
    if os.path.isdir(str(py.path.local(source_path).join(_SIM_DATA.compute_model(data)))):
        animation_dir = py.path.local(target_path).join(_SIM_DATA.compute_model(data))
        pkio.mkdir_parent(str(animation_dir))
        for f in glob.glob(str(py.path.local(source_path).join(_SIM_DATA.compute_model(data), '*'))):
            py.path.local(f).copy(animation_dir)


def generate_parameters_file(data, is_parallel=False):
    _validate_data(data, _SCHEMA)
    res, v = template_common.generate_parameters_file(data)
    v.rpn_variables = _generate_variables(data)

    if is_parallel:
        return res + _generate_full_simulation(data, v)

    if data.get('report', '') == 'twissReport':
        return res + _generate_twiss_simulation(data, v)

    return res + _generate_bunch_simulation(data, v)


def get_application_data(data, **kwargs):
    if data.method == 'get_beam_input_type':
        if data.input_file:
            data.input_type = _sdds_beam_type_from_file(data.input_file)
        return data
    if data.method == 'rpn_value':
        value, error = _parse_expr(data.value, _variables_to_postfix(data.variables))
        if error:
            data.error = error
        else:
            data.result = value
        return data
    if data.method == 'recompute_rpn_cache_values':
        variables = _variables_to_postfix(data.variables)
        for k in data.cache:
            value, error = _parse_expr(k, variables)
            if not error:
                data.cache[k] = value
        return data
    raise RuntimeError('unknown application data method: {}'.format(data.method))


def _file_id(model_id, field_index):
    return '{}{}{}'.format(model_id, _FILE_ID_SEP, field_index)


def _file_name_from_id(file_id, model_data, run_dir):
    return str(run_dir.join(
        _get_filename_for_element_id(file_id.split(_FILE_ID_SEP), model_data)))


def get_data_file(run_dir, model, frame, options=None, **kwargs):
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

    if model == _SIM_DATA.compute_model(None):
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


def import_file(request, tmp_dir=None, test_data=None):
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
    data.models.simulation.name = re.sub(r'\.(lte|ele)$', '', filename, flags=re.IGNORECASE)
    if input_data and not test_data:
        simulation_db.delete_simulation(elegant_common.SIM_TYPE, input_data.models.simulation.simulationId)
    return data


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
    for line in text.split('\n'):
        if line == prev_line:
            continue
        match = re.search('^Starting (\S+) at s\=', line)
        if match:
            name = match.group(1)
            if not re.search('^M\d+\#', name):
                last_element = name
        if want_next_line:
            res += line + '\n'
            want_next_line = False
        elif _is_ignore_error_text(line):
            pass
        elif _is_error_text(line):
            if len(line) < 10:
                want_next_line = True
            else:
                if line != prev_err:
                    res += line + '\n'
                prev_err = line
        prev_line = line
    return res, last_element


def prepare_for_client(data):
    if 'models' not in data:
        return data
    # evaluate rpn values into model.rpnCache
    variables = _variables_to_postfix(data.models.rpnVariables)
    cache = LatticeUtil(data, _SCHEMA).iterate_models(RPNValueIterator(variables)).result
    data.models.rpnCache = cache
    for rpn_var in data.models.rpnVariables:
        v, err = _parse_expr(rpn_var.value, variables)
        if not err:
            cache[rpn_var.name] = v
            if elegant_lattice_importer.is_rpn_value(rpn_var.value):
                cache[rpn_var.value] = v
    return data


def prepare_output_file(run_dir, data):
    if data.report == 'twissReport' or 'bunchReport' in data.report:
        fn = simulation_db.json_filename(template_common.OUTPUT_BASE_NAME, run_dir)
        if fn.exists():
            fn.remove()
            output_file = run_dir.join(_report_output_filename(data.report))
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


def save_report_data(data, run_dir):
    a = copy.deepcopy(data.models[data.report])
    a.frameReport = data.report
    if a.frameReport == 'twissReport':
        a.x = 's'
        a.y = a.y1
    a.frameIndex = 0
    simulation_db.write_result(
        _extract_report_data(str(run_dir.join(_report_output_filename(a.frameReport))), a),
        run_dir=run_dir,
    )


def sim_frame(frame_args):
    r = frame_args.frameReport
    page_count = 0
    for info in _output_info(frame_args.run_dir):
        if info.modelKey == r:
            page_count = info.pageCount
            frame_args.fieldRange = info.fieldRange
    frame_args.y = frame_args.y1
    return _extract_report_data(
        _file_name_from_id(
            frame_args.xFileId,
            frame_args.sim_in,
            frame_args.run_dir,
        ),
        frame_args,
        page_count=page_count,
    )


def validate_file(file_type, path):
    err = None
    if file_type == 'bunchFile-sourceFile':
        err = 'expecting sdds file with (x, xp, y, yp, t, p) or (r, pr, pz, t, pphi) columns'
        if sdds.sddsdata.InitializeInput(_SDDS_INDEX, str(path)) == 1:
            beam_type = _sdds_beam_type(sdds.sddsdata.GetColumnNames(_SDDS_INDEX))
            if beam_type in ('elegant', 'spiffe'):
                sdds.sddsdata.ReadPage(_SDDS_INDEX)
                if len(sdds.sddsdata.GetColumn(_SDDS_INDEX, 0)) > 0:
                    err = None
                else:
                    err = 'sdds file contains no rows'
        sdds.sddsdata.Terminate(_SDDS_INDEX)
    return err


def webcon_generate_lattice(data):
    # Used by Webcon
    util = LatticeUtil(data, _SCHEMA)
    return _generate_lattice(_build_filename_map_from_util(util), util)


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
    for b in _SIM_DATA.lib_file_basenames(data):
        if re.search(r'SCRIPT-commandFile', b):
            os.chmod(str(run_dir.join(b)), stat.S_IRUSR | stat.S_IXUSR)


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


def _build_filename_map(data):
    return _build_filename_map_from_util(LatticeUtil(data, _SCHEMA))


def _build_filename_map_from_util(util):
    return util.iterate_models(OutputFileIterator()).result


def _command_file_extension(model):
    if model._type == 'save_lattice':
        return 'lte'
    if model._type == 'global_settings':
        return 'txt'
    return 'sdds'


def _compute_percent_complete(data, last_element):
    if not last_element:
        return 0
    elements = PKDict()
    for e in data.models.elements:
        elements[e._id] = e
    beamlines = PKDict()
    for b in data.models.beamlines:
        beamlines[b.id] = b
    id = data.models.simulation.visualizationBeamlineId
    beamline_map = PKDict()
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
    if 'distribution_type' in m and 'halogaussian' in m.distribution_type:
        m.distribution_type = m.distribution_type.replace('halogaussian', 'halo(gaussian)')


def _extract_report_data(xFilename, frame_args, page_count=0):
    page_index = frame_args.frameIndex
    xfield = frame_args.x if 'x' in frame_args else frame_args[_X_FIELD]
    # x, column_names, x_def, err
    x_col = sdds_util.extract_sdds_column(xFilename, xfield, page_index)
    if x_col['err']:
        return x_col['err']
    x = x_col['values']
    if not _is_histogram_file(xFilename, x_col['column_names']):
        # parameter plot
        plots = []
        filename = PKDict(
            y1=xFilename,
            #TODO(pjm): y2Filename, y3Filename are not currently used. Would require rescaling x value across files.
            y2=xFilename,
            y3=xFilename,
        )
        for f in ('y1', 'y2', 'y3'):
            if re.search(r'^none$', frame_args[f], re.IGNORECASE) or frame_args[f] == ' ':
                continue
            yfield = frame_args[f]
            y_col = sdds_util.extract_sdds_column(filename[f], yfield, page_index)
            if y_col['err']:
                return y_col['err']
            y = y_col['values']
            plots.append(PKDict(
                field=yfield,
                points=y,
                label=_field_label(yfield, y_col['column_def'][1]),
            ))
        title = ''
        if page_count > 1:
            title = 'Plot {} of {}'.format(page_index + 1, page_count)
        return template_common.parameter_plot(x, plots, frame_args, PKDict(
            title=title,
            y_label='',
            x_label=_field_label(xfield, x_col['column_def'][1]),
        ))
    yfield = frame_args['y1'] if 'y1' in frame_args else frame_args['y']
    y_col = sdds_util.extract_sdds_column(xFilename, yfield, page_index)
    if y_col['err']:
        return y_col['err']
    return template_common.heatmap([x, y_col['values']], frame_args, PKDict(
        x_label=_field_label(xfield, x_col['column_def'][1]),
        y_label=_field_label(yfield, y_col['column_def'][1]),
        title=_plot_title(xfield, yfield, page_index, page_count),
    ))


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
            return PKDict(
                isAuxFile=True,
                filename=filename,
                id=_file_id(id, output_index),
                lastUpdateTime=int(os.path.getmtime(str(file_path))),
            )
        return None
    try:
        if sdds.sddsdata.InitializeInput(_SDDS_INDEX, str(file_path)) != 1:
            return None
        column_names = sdds.sddsdata.GetColumnNames(_SDDS_INDEX)
        plottable_columns = []
        double_column_count = 0
        field_range = PKDict()
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
                try:
                    values = sdds.sddsdata.GetColumn(
                        _SDDS_INDEX,
                        column_names.index(col),
                    )
                except SystemError:
                    # incorrectly generated sdds file
                    break
                if not len(values):
                    pass
                elif len(field_range[col]):
                    field_range[col][0] = min(_safe_sdds_value(min(values)), field_range[col][0])
                    field_range[col][1] = max(_safe_sdds_value(max(values)), field_range[col][1])
                else:
                    field_range[col] = [_safe_sdds_value(min(values)), _safe_sdds_value(max(values))]
        return PKDict(
            isAuxFile=False if double_column_count > 1 else True,
            filename=filename,
            id=_file_id(id, output_index),
            rowCounts=row_counts,
            pageCount=page_count,
            columns=column_names,
            parameters=parameters,
            parameterDefinitions=_parameter_definitions(parameters),
            plottableColumns=plottable_columns,
            lastUpdateTime=int(os.path.getmtime(str(file_path))),
            isHistogram=_is_histogram_file(filename, column_names),
            fieldRange=field_range,
        )
    finally:
        try:
            sdds.sddsdata.Terminate(_SDDS_INDEX)
        except Exception:
            pass


def _find_first_command(data, command_type):
    for m in data.models.commands:
        if m._type == command_type:
            return m
    return None


def _format_field_value(state, model, field, el_type):
    value = model[field]
    if el_type.endswith('StringArray'):
        return ['{}[0]'.format(field), value]
    if el_type == 'RPNValue':
        value = _format_rpn_value(value, is_command=LatticeUtil.is_command(model))
    elif el_type == 'OutputFile':
        value = state.filename_map[_file_id(model._id, state.field_index)]
    elif el_type.startswith('InputFile'):
        value = _SIM_DATA.lib_file_name_with_model_field(LatticeUtil.model_name_for_data(model), field, value)
        if el_type == 'InputFileXY':
            value += '={}+{}'.format(model[field + 'X'], model[field + 'Y'])
    elif el_type == 'BeamInputFile':
        value = 'bunchFile-sourceFile.{}'.format(value)
    elif el_type == 'LatticeBeamlineList':
        value = state.id_map[int(value)].name
    elif el_type == 'ElegantLatticeList':
        if value and value == 'Lattice':
            value = 'elegant.lte'
        else:
            value = value + '.filename.lte'
    elif field == 'command' and LatticeUtil.model_name_for_data(model) == 'SCRIPT':
        for f in ('commandFile', 'commandInputFile'):
            if f in model and model[f]:
                fn = _SIM_DATA.lib_file_name_with_model_field(model.type, f, model[f])
                value = re.sub(r'\b' + re.escape(model[f]) + r'\b', fn, value)
        if model.commandFile:
            value = './' + value
    if not _is_numeric(el_type, value):
        value = '"{}"'.format(value)
    return [field, value]


def _format_rpn_value(value, is_command=False):
    if elegant_lattice_importer.is_rpn_value(value):
        value = _infix_to_postfix(value)
        if is_command:
            return '({})'.format(value)
    return value


def _generate_bunch_simulation(data, v):
    for f in _SCHEMA.model.bunch:
        info = _SCHEMA.model.bunch[f]
        if info[1] == 'RPNValue':
            field = 'bunch_{}'.format(f)
            v[field] = _format_rpn_value(v[field], is_command=True)
    longitudinal_method = int(data.models.bunch.longitudinalMethod)
    # sigma s, sigma dp, dp s coupling
    if longitudinal_method == 1:
        v.bunch_emit_z = 0
        v.bunch_beta_z = 0
        v.bunch_alpha_z = 0
    # sigma s, sigma dp, alpha z
    elif longitudinal_method == 2:
        v.bunch_emit_z = 0
        v.bunch_beta_z = 0
        v.bunch_dp_s_coupling = 0
    # emit z, beta z, alpha z
    elif longitudinal_method == 3:
        v.bunch_sigma_dp = 0
        v.bunch_sigma_s = 0
        v.bunch_dp_s_coupling = 0
    if data.models.bunchSource.inputSource == 'sdds_beam':
        v.bunch_beta_x = 5
        v.bunch_beta_y = 5
        v.bunch_alpha_x = 0
        v.bunch_alpha_x = 0
        if v.bunchFile_sourceFile and v.bunchFile_sourceFile != 'None':
            v.bunchInputFile = _SIM_DATA.lib_file_name_with_model_field('bunchFile', 'sourceFile', v.bunchFile_sourceFile)
            v.bunchFileType = _sdds_beam_type_from_file(v.bunchInputFile)
    if str(data.models.bunch.p_central_mev) == '0':
        run_setup = _find_first_command(data, 'run_setup')
        if run_setup and run_setup.expand_for:
            v.bunchExpandForFile = 'expand_for = "{}",'.format(
                _SIM_DATA.lib_file_name_with_model_field('command_run_setup', 'expand_for', run_setup.expand_for))
    v.bunchOutputFile = _report_output_filename('bunchReport')
    return template_common.render_jinja(SIM_TYPE, v, 'bunch.py')


def _generate_commands(filename_map, util):
    commands = util.iterate_models(
        CommandIterator(filename_map, _format_field_value),
        'commands').result
    res = ''
    for c in commands:
        res +=  '\n' + '&{}'.format(c[0]._type) + '\n'
        for f in c[1]:
            res += '  {} = {},'.format(f[0], f[1]) + '\n'
        res += '&end' + '\n'
    return res


def _generate_full_simulation(data, v):
    util = LatticeUtil(data, _SCHEMA)
    if data.models.simulation.backtracking == '1':
        _setup_backtracking(util)
    filename_map = _build_filename_map_from_util(util)
    v.update(dict(
        commands=_generate_commands(filename_map, util),
        lattice=_generate_lattice(filename_map, util),
        simulationMode=data.models.simulation.simulationMode,
    ))
    return template_common.render_jinja(SIM_TYPE, v)


def _generate_lattice(filename_map, util):
    return util.render_lattice_and_beamline(
        lattice.LatticeIterator(filename_map, _format_field_value),
        quote_name=True)


def _generate_twiss_simulation(data, v):
    max_id = _SIM_DATA.elegant_max_id(data)
    sim = data.models.simulation
    sim.simulationMode = 'serial'
    run_setup = _find_first_command(data, 'run_setup') or PKDict(
        _id=max_id + 1,
        _type='run_setup',
        lattice='Lattice',
        p_central_mev=data.models.bunch.p_central_mev,
    )
    run_setup.use_beamline = sim.activeBeamlineId
    twiss_output = _find_first_command(data, 'twiss_output') or PKDict(
        _id=max_id + 2,
        _type='twiss_output',
        filename='1',
    )
    twiss_output.final_values_only = '0'
    twiss_output.output_at_each_step = '0'
    data.models.commands = [
        run_setup,
        twiss_output,
    ]
    return _generate_full_simulation(data, v)


def _generate_variable(name, variables, visited):
    res = ''
    if name not in visited:
        res += '% ' + '{} sto {}'.format(_format_rpn_value(variables[name]), name) + '\n'
        visited[name] = True
    return res


def _generate_variables(data):
    res = ''
    visited = PKDict()
    variables = PKDict({x.name: x.value for x in data.models.rpnVariables})

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
        expr = rpn
    except Exception as e:
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


def _map_commands_to_lattice(data):
    for cmd in data.models.commands:
        if cmd._type == 'run_setup':
            cmd.lattice = 'Lattice'
            break
    for cmd in data.models.commands:
        if cmd._type == 'run_setup':
            name = cmd.use_beamline.upper()
            for bl in data.models.beamlines:
                if bl.name.upper() == name:
                    cmd.use_beamline = bl.id
                    break


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
    for k in filename_map.keys_in_order:
        filename = filename_map[k]
        id = k.split(_FILE_ID_SEP)
        info = _file_info(filename, run_dir, id[0], id[1])
        if info:
            info.modelKey = 'elementAnimation{}'.format(info.id)
            res.append(info)
    if len(res):
        res[0]['_version'] = _OUTPUT_INFO_VERSION
    simulation_db.write_json(info_file, res)
    return res


def _parameter_definitions(parameters):
    """Convert parameters to useful definitions"""
    res = PKDict()
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
        '{}: must be an expression'.format(tree)
    return ' '.join(_do(tree))


def _plot_title(xfield, yfield, page_index, page_count):
    title_key = xfield + '-' + yfield
    title = ''
    if title_key in _PLOT_TITLE:
        title = _PLOT_TITLE[title_key]
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


def _setup_backtracking(util):

    def _negative(el, fields):
        for f in fields:
            if f in el and el[f]:
                v = str(el[f])
                if re.search(r'^-', v):
                    v = v[1:]
                else:
                    v = '-' + v
                el[f] = v
                break

    util.data = copy.deepcopy(util.data)
    types = PKDict(
        bend=[
            'BRAT', 'BUMPER', 'CSBEND', 'CSRCSBEND', 'FMULT', 'FTABLE', 'KPOLY', 'KSBEND',
            'KQUSE', 'MBUMPER', 'MULT', 'NIBEND', 'NISEPT', 'RBEN', 'SBEN', 'TUBEND'],
        mirror=['LMIRROR'],
    )
    for el in util.data.models.elements:
        # change signs on length and angle fields
        _negative(el, ('l', 'xmax'))
        _negative(el, ('volt', 'voltage', 'initial_v', 'static_voltage'))
        if el.type in types.bend:
            _negative(el, ('angle', 'kick', 'hkick'))
        if el.type in types.mirror:
            _negative(el, ('theta', ))
    util.select_beamline()['items'].reverse()


def _sdds_beam_type(column_names):
    if _contains_columns(column_names, ['x', 'xp', 'y', 'yp', 't', 'p']):
        return 'elegant'
    if _contains_columns(column_names, ['r', 'pr', 'pz', 't', 'pphi']):
        return 'spiffe'
    return ''


def _sdds_beam_type_from_file(filename):
    res = ''
    path = str(_SIM_DATA.lib_file_abspath(filename))
    if sdds.sddsdata.InitializeInput(_SDDS_INDEX, path) == 1:
        res = _sdds_beam_type(sdds.sddsdata.GetColumnNames(_SDDS_INDEX))
    sdds.sddsdata.Terminate(_SDDS_INDEX)
    return res


def _validate_data(data, schema):
    # ensure enums match, convert ints/floats, apply scaling
    enum_info = template_common.validate_models(data, schema)
    _correct_halo_gaussian_distribution_type(data.models.bunch)
    for model_type in ['elements', 'commands']:
        for m in data.models[model_type]:
            template_common.validate_model(m, schema.model[LatticeUtil.model_name_for_data(m)], enum_info)
            _correct_halo_gaussian_distribution_type(m)


def _variables_to_postfix(rpn_variables):
    res = []
    for v in rpn_variables:
        if 'value' not in v:
            pkdlog('rpn var missing value: {}', v['name'])
            v.value = '0'
        res.append(PKDict(
            name=v.name,
            value=_infix_to_postfix(v.value),
        ))
    return res


def _walk_beamline(beamline, index, elements, beamlines, beamline_map):
    # walk beamline in order, adding (<name>#<count> => index) to beamline_map
    for id in beamline['items']:
        if id in elements:
            name = elements[id].name
            if name not in beamline_map:
                beamline_map[name] = 0
            beamline_map[name] += 1
            beamline_map['{}#{}'.format(name.upper(), beamline_map[name])] = index
            index += 1
        else:
            index = _walk_beamline(beamlines[abs(id)], index, elements, beamlines, beamline_map)
    return index
