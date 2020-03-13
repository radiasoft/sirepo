# -*- coding: utf-8 -*-
u"""OPAL execution template.

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkio
from pykern import pkjinja
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdc, pkdlog
from sirepo import simulation_db
from sirepo.template import code_variable
from sirepo.template import lattice
from sirepo.template import sdds_util
from sirepo.template import template_common
from sirepo.template.lattice import LatticeUtil
import h5py
import numpy as np
import re
import sirepo.sim_data


_SIM_DATA, SIM_TYPE, _SCHEMA = sirepo.sim_data.template_globals()

OPAL_INPUT_FILE = 'opal.in'
OPAL_OUTPUT_FILE = 'opal.out'

WANT_BROWSER_FRAME_CACHE = True

_DIM_INDEX = PKDict(
    x=0,
    y=1,
    z=2,
)
_FILE_ID_SEP = '-'
_OPAL_H5_FILE = 'opal.h5'
_OPAL_SDDS_FILE = 'opal.stat'
_ELEMENTS_WITH_TYPE_FIELD = ('CYCLOTRON', 'MONITOR','RFCAVITY')
_HEADER_COMMANDS = ('option', 'filter', 'geometry', 'particlematterinteraction', 'wake')
_TWISS_FILE_NAME = 'twiss.out'
#TODO(pjm): parse from opal files into schema
_OPAL_PI = 3.14159265358979323846
_OPAL_CONSTANTS = PKDict(
    PI=_OPAL_PI,
    TWOPI=_OPAL_PI * 2.0,
    RADDEG=180.0 / _OPAL_PI,
    DEGRAD=_OPAL_PI / 180.0,
    E=2.7182818284590452354,
    EMASS=0.51099892e-03,
    PMASS=0.93827204e+00,
    HMMASS=0.939277e+00,
    UMASS=238 * 0.931494027e+00,
    CMASS=12 * 0.931494027e+00,
    MMASS=0.10565837,
    DMASS=2*0.931494027e+00,
    XEMASS=124*0.931494027e+00,
    CLIGHT=299792458.0,
    P0=1,
    SEED=123456789,
)


class OpalElementIterator(lattice.ElementIterator):
    def is_ignore_field(self, field):
        return field == 'name'

class OpalOutputFileIterator(lattice.ModelIterator):
    def __init__(self):
        self.result = PKDict(
            keys_in_order=[],
        )
        self.model_index = PKDict()

    def field(self, model, field_schema, field):
        self.field_index += 1
        # for now only interested in element outfn output files
        if field == 'outfn' and field_schema[1] == 'OutputFile':
            filename = '{}.{}.h5'.format(model.name, field)
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


def background_percent_complete(report, run_dir, is_running):
    res = PKDict(
        percentComplete=0,
        frameCount=0,
    )
    if is_running:
        data = simulation_db.read_json(run_dir.join(template_common.INPUT_BASE_NAME))
        #TODO(pjm): determine total frame count and set percentComplete
        res.frameCount = _read_frame_count(run_dir) - 1
        return res
    if run_dir.join('{}.json'.format(template_common.INPUT_BASE_NAME)).exists():
        res.frameCount = _read_frame_count(run_dir)
        if res.frameCount > 0:
            res.percentComplete = 100
            res.outputInfo = _output_info(run_dir)
    return res


def get_application_data(data, **kwargs):
    if data.method == 'compute_particle_ranges':
        return template_common.compute_field_range(data, _compute_range_across_frames)
    if data.method == 'rpn_value':
        v, err = _code_var(data.variables).eval_var(data.value)
        if err:
            data.error = err
        else:
            data.result = v
        return data
    if data.method == 'recompute_rpn_cache_values':
        _code_var(data.variables).recompute_cache(data.cache)
        return data
    if data.method == 'validate_rpn_delete':
        model_data = simulation_db.read_json(
            simulation_db.sim_data_file(SIM_TYPE, data.simulationId))
        data.error = _code_var(data.variables).validate_var_delete(data.name, model_data, _SCHEMA)
        return data
    raise AssertionError('unknown get_application_data: {}'.format(data))


def get_data_file(run_dir, model, frame, options=None, **kwargs):
    filename = None
    if model == 'bunchAnimation' or model == 'plotAnimation' or 'bunchReport' in model:
        filename = _OPAL_H5_FILE
    elif model == 'plot2Animation':
        filename = _OPAL_SDDS_FILE
    else:
        assert False, 'file: {}'.format(model)
    path = run_dir.join(filename)
    with open(str(path)) as f:
        return path.basename, f.read(), 'application/octet-stream'


def post_execution_processing(
        success_exit=True,
        is_parallel=True,
        run_dir=None,
        **kwargs
):
    if success_exit:
        return None
    if is_parallel:
        return _parse_opal_log(run_dir)
    e = _parse_opal_log(run_dir)
    if re.search(r'Singular matrix', e):
        e = 'Twiss values could not be computed: Singular matrix'
    return e


def prepare_for_client(data):
    if 'models' not in data:
        return data
    data.models.rpnCache = _code_var(data.models.rpnVariables).compute_cache(data, _SCHEMA)
    return data


def prepare_output_file(run_dir, data):
    report = data['report']
    if 'bunchReport' in report or 'twissReport' in report:
        fn = simulation_db.json_filename(template_common.OUTPUT_BASE_NAME, run_dir)
        if fn.exists():
            fn.remove()
            try:
                save_report_data(data, run_dir)
            except IOError:
                # the output file isn't readable
                pass


def python_source_for_model(data, model):
    return _generate_parameters_file(data)


def save_report_data(data, run_dir):
    report = data.models[data.report]
    res = None
    if data.report == 'twissReport':
        report['x'] = 's'
        col_names, rows = _read_data_file(run_dir.join(_TWISS_FILE_NAME))
        x = _column_data(report.x, col_names, rows)
        y_range = None
        plots = []
        for f in ('y1', 'y2', 'y3'):
            if report[f] == 'none':
                continue
            plots.append({
                'points': _column_data(report[f], col_names, rows),
                'label': '{} {}'.format(report[f], _units(report[f])),
            })
        res = PKDict(
            title='',
            x_range=[min(x), max(x)],
            y_label='',
            x_label='{} {}'.format(report.x, _units(report.x)),
            x_points=x,
            plots=plots,
            y_range=template_common.compute_plot_color_and_range(plots),
        )
    elif 'bunchReport' in data.report:
        res = _bunch_plot(report, run_dir, 0)
        res.title = ''
    else:
        raise AssertionError('unknown report: {}'.format(report))
    template_common.write_sequential_result(
        res,
        run_dir=run_dir,
    )


def sim_frame(frame_args):
    r = frame_args.frameReport
    if r == 'bunchAnimation':
        return sim_frame_bunchAnimation(frame_args)
    if r == 'plotAnimation':
        return sim_frame_plotAnimation(frame_args)
    if r == 'plot2Animation':
        return sim_frame_plot2Animation(frame_args)
    # elementAnimations
    page_count = 0
    filename = None
    for info in _output_info(frame_args.run_dir):
        if info.modelKey == r:
            filename = info.filename
            break
    return _bunch_plot(frame_args, frame_args.run_dir, frame_args.frameIndex, filename)


def sim_frame_bunchAnimation(frame_args):
    a = frame_args.sim_in.models.bunchAnimation
    a.update(frame_args)
    return _bunch_plot(a, a.run_dir, a.frameIndex)


def sim_frame_plotAnimation(frame_args):

    def _walk_file(h5file, key, step, res):
        if key:
            for field in res.values():
                field.points.append(h5file[key].attrs[field.name][field.index])
        else:
            for field in res.values():
                _units_from_hdf5(h5file, field)


    res = PKDict()
    for dim in 'x', 'y1', 'y2', 'y3':
        parts = frame_args[dim].split(' ')
        if parts[0] == 'none':
            continue
        res[dim] = PKDict(
            label=frame_args[dim],
            dim=dim,
            points=[],
            name=parts[0],
            index=_DIM_INDEX[parts[1]] if len(parts) > 1 else 0,
        )
    _iterate_hdf5_steps(frame_args.run_dir.join(_OPAL_H5_FILE), _walk_file, res)
    plots = []
    for field in res.values():
        if field.dim != 'x':
            plots.append(field)
    return template_common.parameter_plot(
        res.x.points,
        plots,
        PKDict(),
        PKDict(
            title='',
            y_label='',
            x_label=res.x.label,
        ),
    )


def sim_frame_plot2Animation(frame_args):

    x = None
    plots = []
    for f in ('x', 'y1', 'y2', 'y3'):
        name = frame_args[f].replace(' ', '_')
        if name == 'none':
            continue
        col = sdds_util.extract_sdds_column(str(frame_args.run_dir.join(_OPAL_SDDS_FILE)), name, 0)
        if col.err:
            return col.err
        field = PKDict(
            points=col['values'],
            label=frame_args[f],
        )
        _field_units(col.column_def[1], field)
        if f == 'x':
            x = field
        else:
            plots.append(field)
    return template_common.parameter_plot(x.points, plots, {}, {
        'title': '',
        'y_label': '',
        'x_label': x.label,
    })


def write_parameters(data, run_dir, is_parallel):
    pkio.write_text(
        run_dir.join(OPAL_INPUT_FILE),
        _generate_parameters_file(data),
    )


def _bunch_plot(report, run_dir, idx, filename=_OPAL_H5_FILE):
    res = PKDict()
    title = 'Step {}'.format(idx)
    with h5py.File(str(run_dir.join(filename)), 'r') as f:
        for field in ('x', 'y'):
            res[field] = PKDict(
                name=report[field],
                points=np.array(f['/Step#{}/{}'.format(idx, report[field])]),
                label=report[field],
            )
            _units_from_hdf5(f, res[field])
        if 'SPOS' in f['/Step#{}'.format(idx)].attrs:
            title += ', SPOS {0:.5f}m'.format(f['/Step#{}'.format(idx)].attrs['SPOS'][0])
    return template_common.heatmap([res.x.points, res.y.points], report, PKDict(
        x_label=res.x.label,
        y_label=res.y.label,
        title=title,
    ))


def _code_var(variables):
    return code_variable.CodeVar(
        variables,
        code_variable.PurePythonEval(_OPAL_CONSTANTS),
    )


def _compute_range_across_frames(run_dir, data):
    def _walk_file(h5file, key, step, res):
        if key:
            for field in res:
                v = np.array(h5file['/{}/{}'.format(key, field)])
                min1, max1 = v.min(), v.max()
                if res[field]:
                    if res[field][0] > min1:
                        res[field][0] = min1
                    if res[field][1] < max1:
                        res[field][1] = max1
                else:
                    res[field] = [min1, max1]
    res = PKDict()
    for v in _SCHEMA.enum.PhaseSpaceCoordinate:
        res[v[0]] = None
    return _iterate_hdf5_steps(run_dir.join(_OPAL_H5_FILE), _walk_file, res)


def _column_data(col, col_names, rows):
    idx = col_names.index(col)
    assert idx >= 0, 'invalid col: {}'.format(col)
    res = []
    for row in rows:
        res.append(float(row[idx]))
    return res


def _field_units(units, field):
    if units == '1':
        units = ''
    elif units[0] == 'M' and len(units) > 1:
        units = re.sub(r'^.', '', units)
        field.points = (np.array(field.points) * 1e6).tolist()
    elif units[0] == 'G' and len(units) > 1:
        units = re.sub(r'^.', '', units)
        field.points = (np.array(field.points) * 1e9).tolist()
    elif units == 'ns':
        units = 's'
        field.points = (np.array(field.points) / 1e9).tolist()
    if units:
        if re.search(r'^#', units):
            field.label += ' ({})'.format(units)
        else:
            field.label += ' [{}]'.format(units)
    field.units = units


def _file_id(model_id, field_index):
    return '{}{}{}'.format(model_id, _FILE_ID_SEP, field_index)


def _find_run_method(commands):
    for command in commands:
        if command._type == 'track' and command.run_method:
            return command.run_method
    return 'THIN'


def _format_field_value(state, model, field, el_type):
    value = model[field]
    if el_type == 'Boolean':
        value = 'true' if value == '1' else 'false'
    elif el_type == 'InputFile':
        value = '"{}"'.format(
            _SIM_DATA.lib_file_name_with_model_field(LatticeUtil.model_name_for_data(model), field, value))
    elif el_type == 'OutputFile':
        ext = 'dat' if model.get('_type', '') == 'list' else 'h5'
        value = '"{}.{}.{}"'.format(model.name, field, ext)
    elif re.search(r'List$', el_type):
        value = state.id_map[int(value)].name
    # elif LatticeUtil.is_command(model):
        #TODO(pjm): determine the general case where values need quotes
        # if model._type == 'run' and field == 'method':
        #     value = '"{}"'.format(value)
        #value = '"{}"'.format(value)
        # if el_type == 'Boolean' or el_type == 'RPNValue':
        #     pass
        # elif value:
        #     value = '"{}"'.format(value)
    elif re.search(r'String', el_type):
        if len(str(value)):
            value = '"{}"'.format(value)
    elif LatticeUtil.is_command(model):
        if el_type != 'RPNValue' and len(str(value)):
            value = '"{}"'.format(value)
    elif not LatticeUtil.is_command(model):
        if model.type in _ELEMENTS_WITH_TYPE_FIELD and '_type' in field:
            return ['type', value]
    if len(str(value)):
        return [field, value]
    return None


def _generate_commands(util, is_header):
    # reorder command so OPTION and list commands come first
    commands = []
    key = None
    if is_header:
        key = 'header_commands'
        # add header commands in order, with option first
        for ctype in _HEADER_COMMANDS:
            for c in util.data.models.commands:
                if c._type == ctype:
                    commands.append(c)
    else:
        key = 'other_commands'
        for c in util.data.models.commands:
            if c._type not in _HEADER_COMMANDS:
                commands.append(c)
    util.data.models[key] = commands
    res = util.render_lattice(
        util.iterate_models(
            OpalElementIterator(None, _format_field_value),
            key,
        ).result,
        want_semicolon=True)
    # separate run from track, add endtrack
    #TODO(pjm): better to have a custom element generator for this case
    lines = []
    for line in res.splitlines():
        m = re.match('(.*?: track,.*?)(run_.*?)(;|,[^r].*)', line)
        if m:
            lines.append('{}{}'.format(re.sub(r',$', '', m.group(1)), m.group(3)))
            lines.append(' run, {};'.format(re.sub(r'run_', '', m.group(2))))
            lines.append('endtrack;')
        else:
            lines.append(line)
    return '\n'.join(lines)


def _generate_lattice(util, code_var, beamline_id):
    res = util.render_lattice(
        util.iterate_models(
            OpalElementIterator(None, _format_field_value),
            'elements',
        ).result,
        want_semicolon=True) + '\n'
    count_by_name = PKDict()
    names = []
    res += _generate_beamline(util, code_var, count_by_name, beamline_id, 0, names)[0]
    res += '{}: LINE=({});\n'.format(
        util.id_map[beamline_id].name,
        ','.join(names),
    )
    return res


def _generate_beamline(util, code_var, count_by_name, beamline_id, edge, names):
    res = ''
    run_method = _find_run_method(util.data.models.commands)
    for item_id in util.id_map[beamline_id]['items']:
        item = util.id_map[item_id]
        if 'type' in item:
            # element
            name = item.name
            if name not in count_by_name:
                count_by_name[name] = 0
            name = '"{}#{}"'.format(name, count_by_name[name])
            names.append(name)
            count_by_name[item.name] += 1
            if run_method == 'OPAL-CYCL' or run_method == 'CYCLOTRON-T':
                res += '{}: {};\n'.format(name, item.name)
            else:
                res += '{}: {},elemedge={};\n'.format(name, item.name, edge)
            edge += code_var.eval_var(item.l)[0]
        else:
            # beamline
            text, edge = _generate_beamline(util, code_var, count_by_name, item_id, edge, names)
            res += text
    return res, edge


def _find_first_command(data, command_type):
    for cmd in data.models.commands:
        if cmd._type == command_type:
            return cmd
    assert False, 'command not found: {}'.format(command_type)


def _generate_parameters_file(data):
    res, v = template_common.generate_parameters_file(data)
    util = LatticeUtil(data, _SCHEMA)
    code_var = _code_var(data.models.rpnVariables)
    report = data.get('report', '')

    if 'bunchReport' in report:
        # keep only first distribution and beam in command list
        beam = _find_first_command(data, 'beam')
        distribution = _find_first_command(data, 'distribution')
        v.beamName = beam.name
        v.distributionName = distribution.name
        data.models.commands = [
            _find_first_command(data, 'option'),
            beam,
            distribution,
        ]
    else:
        if report == 'twissReport':
            beamline_id = util.select_beamline().id
        else:
            beamline_id = _find_first_command(util.data, 'track').line
        v.lattice = _generate_lattice(util, code_var, beamline_id)
        v.use_beamline = util.select_beamline().name


    v.update(dict(
        variables=_generate_variables(code_var, data),
        header_commands=_generate_commands(util, True),
        commands=_generate_commands(util, False),
    ))
    if 'bunchReport' in report:
        return template_common.render_jinja(SIM_TYPE, v, 'bunch.in')
    if report == 'twissReport':
        v.twiss_file_name = _TWISS_FILE_NAME
        return template_common.render_jinja(SIM_TYPE, v, 'twiss.in')
    return template_common.render_jinja(SIM_TYPE, v, 'parameters.in')


def _generate_variable(name, variables, visited):
    res = ''
    if name not in visited:
        res += 'REAL {} = {};\n'.format(name, variables[name])
        visited[name] = True
    return res


def _generate_variables(code_var, data):
    res = ''
    visited = PKDict()

    for name in sorted(code_var.variables):
        for dependency in code_var.get_expr_dependencies(code_var.postfix_variables[name]):
            res += _generate_variable(dependency, code_var.variables, visited)
        res += _generate_variable(name, code_var.variables, visited)
    return res


def _iterate_hdf5_steps(path, callback, state):
    with h5py.File(str(path), 'r') as f:
        step = 0
        key = 'Step#{}'.format(step)
        while key in f:
            callback(f, key, step, state)
            step += 1
            key = 'Step#{}'.format(step)
        callback(f, None, -1, state)
    return state


def _output_info(run_dir):
    #TODO(pjm): cache to file with version, similar to template.elegant
    data = simulation_db.read_json(run_dir.join(template_common.INPUT_BASE_NAME))
    files = LatticeUtil(data, _SCHEMA).iterate_models(OpalOutputFileIterator()).result
    res = []
    for k in files.keys_in_order:
        id = k.split(_FILE_ID_SEP)
        if run_dir.join(files[k]).exists():
            res.append(PKDict(
                modelKey='elementAnimation{}'.format(id[0]),
                filename=files[k],
                isHistogram=True,
            ))
    return res


def _parse_opal_log(run_dir):
    res = ''
    with pkio.open_text(run_dir.join(OPAL_OUTPUT_FILE)) as f:
        prev_line = ''
        for line in f:
            if re.search(r'^Error.*?>', line):
                line = re.sub(r'^Error.*?>\s*\**\s*', '', line.rstrip())
                if re.search(r'1DPROFILE1-DEFAULT', line):
                    continue
                if line and line != prev_line:
                    res += line + '\n'
                prev_line = line
    if res:
        return res
    return 'An unknown error occurred'


def _read_data_file(path):
    col_names = []
    rows = []
    with pkio.open_text(str(path)) as f:
        col_names = []
        rows = []
        mode = ''
        for line in f:
            if '---' in line:
                if mode == 'header':
                    mode = 'data'
                elif mode == 'data':
                    break
                if not mode:
                    mode = 'header'
                continue
            line = re.sub('\0', '', line)
            if mode == 'header':
                col_names = re.split('\s+', line.lower())
            elif mode == 'data':
                #TODO(pjm): separate overlapped columns. Instead should explicitly set field dimensions
                line = re.sub('(\d)(\-\d)', r'\1 \2', line)
                line = re.sub(r'(\.\d{3})(\d+\.)', r'\1 \2', line)
                rows.append(re.split('\s+', line))
    return col_names, rows


def _read_frame_count(run_dir):
    def _walk_file(h5file, key, step, res):
        if key:
            res[0] = step + 1
    try:
        return _iterate_hdf5_steps(run_dir.join(_OPAL_H5_FILE), _walk_file, [0])[0]
    except IOError:
        pass
    return 0


def _units(twiss_field):
    if twiss_field in ('betx', 'bety', 'dx'):
        return '[m]'
    return ''


def _units_from_hdf5(h5file, field):
    return _field_units(str(h5file.attrs['{}Unit'.format(field.name)]), field)
