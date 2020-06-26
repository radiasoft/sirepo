# -*- coding: utf-8 -*-
u"""MAD-X execution template.

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkcompat
from pykern import pkio
from pykern import pkjinja
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdc, pkdlog
from sirepo import simulation_db
from sirepo.template import code_variable
from sirepo.template import elegant_command_importer
from sirepo.template import elegant_lattice_importer
from sirepo.template import lattice
from sirepo.template import madx_converter, madx_parser
from sirepo.template import sdds_util
from sirepo.template import template_common
from sirepo.template.template_common import ParticleEnergy
from sirepo.template.lattice import LatticeUtil
import copy
import functools
import math
import numpy as np
import pykern.pkinspect
import re
import scipy.constants
import sirepo.sim_data


MADX_INPUT_FILE = 'madx.in'

MADX_OUTPUT_FILE = 'madx.out'

_INITIAL_REPORTS = ['twissEllipseReport', 'bunchReport']

_FIELD_LABEL = PKDict(
    alfx='alfx [1]',
    alfy='alfy [1]',
    betx='betx [m]',
    bety='bety [m]',
    dpx='dpx [1]',
    dpy='dpy [1]',
    dx='dx[m]',
    dy='dy [m]',
    mux='mux [2π]',
    muy='muy [2π]',
    px='px [1]',
    py='py [1]',
    s='s [m]',
    x='x [m]',
    y='y [m]',
)

_PI = 4 * math.atan(1)

_METHODS = template_common.RPN_METHODS + []

_MADX_CONSTANTS = PKDict(
    pi=_PI,
    twopi=_PI * 2.0,
    raddeg=180.0 / _PI,
    degrad=_PI / 180.0,
    e=math.exp(1),
    emass=0.510998928e-03,
    pmass=0.938272046e+00,
    nmass=0.931494061+00,
    mumass=0.1056583715,
    clight=299792458.0,
    qelect=1.602176565e-19,
    hbar=6.58211928e-25,
    erad=2.8179403267e-15,
)

_PTC_PARTICLES_FILE = 'ptc_particles.madx'

_PTC_TRACK_COMMAND = 'ptc_track'

_PTC_TRACK_USE_ONETABLE = True

_SIM_DATA, SIM_TYPE, _SCHEMA = sirepo.sim_data.template_globals()

_TFS_FILE_EXTENSION = 'tfs'

_TWISS_OUTPUT_FILE = f'twiss.{_TFS_FILE_EXTENSION}'

class MadxOutputFileIterator(lattice.ModelIterator):
    def __init__(self):
        self.result = PKDict(
            keys_in_order=[],
        )
        self.model_index = PKDict()

    def field(self, model, field_schema, field):
        self.field_index += 1
        if field_schema[1] == 'OutputFile':
            b = '{}{}.{}'.format(
                model._type,
                self.model_index[self.model_name] if self.model_index[self.model_name] > 1 else '',
                field,
            )
            self.result[model._id] = PKDict(
                filename=b + f'.{_TFS_FILE_EXTENSION}',
                model_type=model._type,
                purebasename=b,
                ext=_TFS_FILE_EXTENSION,
            )
            self.result.keys_in_order.append(model._id)

    def start(self, model):
        self.field_index = 0
        self.model_name = LatticeUtil.model_name_for_data(model)
        if self.model_name in self.model_index:
            self.model_index[self.model_name] += 1
        else:
            self.model_index[self.model_name] = 1


def background_percent_complete(report, run_dir, is_running):
    if is_running:
        return PKDict(
            percentComplete=0,
            frameCount=0,
        )
    return PKDict(
        percentComplete=100,
        frameCount=1,
        outputInfo=_output_info(run_dir),
    )


def get_application_data(data, **kwargs):
    assert 'method' in data
    assert data.method in _METHODS, \
        'unknown application data method: {}'.format(data.method)
    cv = code_variable.CodeVar(
        data.variables,
        code_variable.PurePythonEval(_MADX_CONSTANTS),
        case_insensitive=True,
    )
    if data.method == 'rpn_value':
        # accept array of values enclosed in curly braces
        if re.search(r'^\{.*\}$', data.value):
            data.result = ''
            return data
        v, err = cv.eval_var(data.value)
        if err:
            data.error = err
        else:
            data.result = v
        return data
    if data.method == 'recompute_rpn_cache_values':
        cv(data.variables).recompute_cache(data.cache)
        return data
    if data.method == 'validate_rpn_delete':
        model_data = simulation_db.read_json(
            simulation_db.sim_data_file(data.simulationType, data.simulationId))
        data.error = cv(data.variables).validate_var_delete(
            data.name,
            model_data,
            _SCHEMA
        )
        return data


def import_file(req, **kwargs):
    text = pkcompat.from_bytes(req.file_stream.read())
    assert re.search(r'\.madx$', req.filename, re.IGNORECASE), \
        'invalid file extension, expecting .madx'
    data = madx_parser.parse_file(text, downcase_variables=True)
    _fixup_madx(data)
    # TODO(e-carlin): need to clean this up. copied from elegant
    data.models.simulation.name = re.sub(
        r'\.madx$',
        '',
        req.filename,
        flags=re.IGNORECASE
    )
    return data


def is_initial_report(rpt):
    return re.sub(r'\d+$', '', rpt) in _INITIAL_REPORTS


def madx_code_var(variables):
    return _code_var(variables)


def prepare_for_client(data):
    if 'models' not in data:
        return data
    data.models.rpnCache = madx_code_var(data.models.rpnVariables).compute_cache(data, _SCHEMA)
    return data


def prepare_sequential_output_file(run_dir, data):
    r = data.report
    if r == 'twissReport':
        f = simulation_db.json_filename(template_common.OUTPUT_BASE_NAME, run_dir)
        if f.exists():
            f.remove()
            save_sequential_report_data(data, run_dir)


# TODO(e-carlin): fixme - I don't return python
def python_source_for_model(data, model):
    return _generate_parameters_file(data)


def sim_frame(frame_args):
    d = frame_args.sim_in
    d.report = frame_args.frameReport
    m = None
    try:
        m = d.models[d.report]
    except KeyError:
        # It may not exist in models because a command was addedd (ex twiss)
        # and we don't have an animation model for it yet.
        m  = PKDict()
        _SIM_DATA.update_model_defaults(m, 'elementAnimation')
        d.models[d.report] = m
    m.update((k, frame_args[k]) for k in frame_args.keys() & m.keys())
    return _extract_report_data(d, frame_args.run_dir)


def save_sequential_report_data(data, run_dir):
    template_common.write_sequential_result(
        _extract_report_data(data, run_dir),
        run_dir=run_dir,
    )


def write_parameters(data, run_dir, is_parallel):
    """Write the parameters file

    Args:
        data (dict): input
        run_dir (py.path): where to write
        is_parallel (bool): run in background?
    """
    pkio.write_text(
        run_dir.join(_PTC_PARTICLES_FILE),
        _generate_ptc_particles_file(data),
    )
    pkio.write_text(
        run_dir.join(MADX_INPUT_FILE),
        _generate_parameters_file(data),
    )


def _add_commands(data, util):
    commands = data.models.commands
    # set the selected beamline depending on the lattice or visualization
    idx = next(i for i, cmd in enumerate(commands) if cmd._type == 'beam')
    commands.insert(idx + 1, PKDict(
        _type='use',
        sequence=util.select_beamline().id,
    ))
    if not util.find_first_command(data, 'ptc_create_layout'):
        return
    # insert call and ptc_observe commands after ptc_create_layout
    idx = next(i for i, cmd in enumerate(commands) if cmd._type == 'ptc_create_layout')
    commands.insert(idx + 1, PKDict(
        _type='call',
        file=_PTC_PARTICLES_FILE,
    ))
    commands.insert(idx + 2, PKDict(
        _type='ptc_observe',
        place='{}$END'.format(util.select_beamline().name.upper()),
    ))


def _build_filename_map(data):
    return _build_filename_map_from_util(LatticeUtil(data, _SCHEMA))


def _build_filename_map_from_util(util):
    return util.iterate_models(MadxOutputFileIterator()).result


def _code_var(variables):
    return code_variable.CodeVar(
        variables,
        code_variable.PurePythonEval(_MADX_CONSTANTS),
        case_insensitive=True,
    )

def _extract_report_bunchReport(data, run_dir):
    # read from file?  store on model?
    parts = _ptc_particles(
        _get_initial_twiss_params(data),
        data.models.simulation.numberOfParticles
    )
    labels = []
    res = []
    r_model = data.models[data.report]
    for dim in ('x', 'y'):
        c = _SCHEMA.constants.phaseSpaceParticleMap[r_model[dim]]
        res.append(parts[c[0]][c[1]])
        labels.append(r_model[dim])

    return template_common.heatmap(
        res,
        PKDict(histogramBins=100),
        PKDict(
            x_label=labels[0],
            y_label=labels[1],
            title='BUNCH',
        )
    )


def _extract_report_data(data, run_dir):
    r = data.get('report', data.get('frameReport'))
    m = re.split(r'(\d+)', r)
    f = getattr(
        pykern.pkinspect.this_module(),
        '_extract_report_' + m[0] if m else r
    )
    f = functools.partial(f, data, run_dir)
    if 'Animation' in r:
        f = functools.partial(f, filename=_filename_for_report(run_dir, r))
    return f()


def _extract_report_ptcAnimation(data, run_dir, filename):
    m = data.models[data.report]
    t = madx_parser.parse_tfs_file(run_dir.join(filename))
    return template_common.heatmap(
        [_to_floats(t[m.x]), _to_floats(t[m.y])],
        m,
        PKDict(
            x_label=_FIELD_LABEL[m.x],
            y_label=_FIELD_LABEL[m.y],
            title=data.models.simulation.name,
        ),
    )


def _extract_report_twissAnimation(*args, **kwargs):
    return _extract_report_twissReport(*args, **kwargs)


def _extract_report_twissEllipseReport(data, run_dir):
    util = LatticeUtil(data, _SCHEMA)
    m = util.find_first_command(data, 'twiss')
    # must an initial twiss always exist?
    if not m:
        return template_common.parameter_plot([], [], None, PKDict())
    r_model = data.models[data.report]
    dim = r_model.dim
    plots = []
    n_pts = 200
    theta = np.arange(0, 2. * np.pi * (n_pts / (n_pts - 1)), 2. * np.pi / n_pts)
    alf = 'alf{}'.format(dim)
    bet = 'bet{}'.format(dim)
    a = float(m[alf])
    b = float(m[bet])
    g = (1. + a * a) / b
    eta = 'e{}'.format(dim)
    e = m[eta] if eta in m else 1.0
    phi = _twiss_ellipse_rotation(a, b)
    th = theta - phi
    mj = math.sqrt(e * b)
    mn = 1.0 / mj
    r = np.power(
        mn * np.cos(th) * np.cos(th) + mj * np.sin(th) * np.sin(th),
        -0.5
    )
    x = r * np.cos(theta)
    y = r * np.sin(theta)
    p = PKDict(field=dim, points=y.tolist(), label=f'{dim}\' [rad]')
    plots.append(
        p
    )
    return template_common.parameter_plot(
        x.tolist(),
        plots,
        {},
        PKDict(
            title=f'{data.models.simulation.name} a{dim} = {a} b{dim} = {b} g{dim} = {g}',
            y_label='',
            x_label=f'{dim} [m]'
        )
    )


def _extract_report_twissReport(data, run_dir, filename=_TWISS_OUTPUT_FILE):
    t = madx_parser.parse_tfs_file(run_dir.join(filename))
    plots = []
    m = data.models[data.report]
    for f in ('y1', 'y2', 'y3'):
        if m[f] == 'none':
            continue
        plots.append(
            PKDict(field=m[f], points=_to_floats(t[m[f]]), label=_FIELD_LABEL[m[f]])
        )
    x = m.get('x') or 's'
    return template_common.parameter_plot(
        _to_floats(t[x]),
        plots,
        m,
        PKDict(title=data.models.simulation.name, y_label='', x_label=_FIELD_LABEL[x])
    )


def _filename_for_report(run_dir, report):
    for info in _output_info(run_dir):
        if info.modelKey == report:
            return info.filename
    raise AssertionError(f'no output file for report={report}')


def _fixup_madx(madx):
    # move imported beam over default-data.json beam
    # remove duplicate twiss
    # remove "use" commands
    beam_idx = None
    found_twiss = False
    res = []
    for cmd in madx.models.commands:
        if cmd._type == 'use':
            continue
        if cmd._type == 'beam':
            if beam_idx is None:
                beam_idx = madx.models.commands.index(cmd)
            else:
                res[beam_idx] = cmd
                continue
        elif cmd._type == 'twiss':
            if found_twiss:
                continue
            found_twiss = True
        res.append(cmd)
    madx.models.commands = res


def _format_field_value(state, model, field, el_type):
    v = model[field]
    if el_type == 'Boolean':
        v = 'true' if v == '1' else 'false'
    elif el_type == 'LatticeBeamlineList':
        v = state.id_map[int(v)].name
    elif el_type == 'OutputFile':
        v = '"{}"'.format(state.filename_map[model._id].filename)
    return [field, v]


def _generate_commands(filename_map, util):
    res = ''
    for c in util.iterate_models(
            lattice.ElementIterator(filename_map, _format_field_value), 'commands'
    ).result:
        res += f'{c[0]._type}'
        for f in c[1]:
           res += f', {f[0]}={f[1]}'
        t = c[0]._type
        if t == _PTC_TRACK_COMMAND:
            res += (f', dump=true, {"onetable=true, " if _PTC_TRACK_USE_ONETABLE else ""}'
                    f'file={filename_map[c[0]._id].purebasename}'
                    f', extension=.{_TFS_FILE_EXTENSION}')
        res += ';\n'
    return res


def _generate_lattice(filename_map, util):
    return util.render_lattice_and_beamline(
        lattice.LatticeIterator(filename_map, _format_field_value),
        want_semicolon=True)


def _generate_parameters_file(data):
    res, v = template_common.generate_parameters_file(data)

    v.report = re.sub(r'\d+$', '', data.get('report', ''))
    if v.report in _INITIAL_REPORTS:
        # these reports do not require running madx first
        v.initialTwissParameters = _get_initial_twiss_params(data)
        v.numParticles = data.models.simulation.numberOfParticles
        v.particleFile = simulation_db.simulation_dir(SIM_TYPE, data.simulationId) \
            .join(data.report).join('ptc_particles.txt')
        res = template_common.render_jinja(SIM_TYPE, v, 'bunch.py')
        return res

    util = LatticeUtil(data, _SCHEMA)
    filename_map = _build_filename_map_from_util(util)
    report = data.get('report', '')
    code_var = _code_var(data.models.rpnVariables)
    v.twissOutputFilename = _TWISS_OUTPUT_FILE
    v.lattice = _generate_lattice(filename_map, util)
    v.variables = _generate_variables(code_var, data)

    v.useBeamline = util.select_beamline().name
    if report == 'twissReport':
        v.twissOutputFilename = _TWISS_OUTPUT_FILE
        return template_common.render_jinja(SIM_TYPE, v, 'twiss.madx')
    _add_commands(data, util)
    v.commands = _generate_commands(filename_map, util)
    v.hasTwiss = bool(util.find_first_command(data, 'twiss'))
    if not v.hasTwiss:
        v.twissOutputFilename = _TWISS_OUTPUT_FILE
    return template_common.render_jinja(SIM_TYPE, v, 'parameters.madx')


def _generate_ptc_particles_file(data):
    return template_common.render_jinja(
        SIM_TYPE,
        PKDict(start_commands=_ptc_start_commands(data)),
        _PTC_PARTICLES_FILE,
    )


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


def _get_initial_twiss_params(data):
    p = PKDict(
        x=PKDict(),
        y=PKDict()
    )
    util = LatticeUtil(data, _SCHEMA)
    m = util.find_first_command(data, 'twiss')
    if not m:
        return p
    for dim in ('x', 'y'):
        alf = 'alf{}'.format(dim)
        bet = 'bet{}'.format(dim)
        eta = 'e{}'.format(dim)
        a = m[alf]
        b = m[bet]
        p[dim].alpha = a
        p[dim].beta = b
        p[dim].emittance = m[eta] if eta in m else 1.0
        p[dim].gamma = (1. + a * a) / b
    return p


def _output_info(run_dir):
    files = _build_filename_map(
        simulation_db.read_json(run_dir.join(template_common.INPUT_BASE_NAME))
    )
    res = []
    for k in files.keys_in_order:
        f = files[k]
        n = f.filename
        if 'ptc' in f.model_type:
            # Madx appends "one" to file purebasename if onetable is used
            n = f'{f.purebasename}{"one" if _PTC_TRACK_USE_ONETABLE else ""}.{f.ext}'
        if run_dir.join(n).exists():
            res.append(PKDict(
                modelKey='{}{}'.format(
                    ('twiss' if f.model_type == 'twiss' else 'ptc') + 'Animation',
                    k,
                ),
                filename=n,
                isHistogram='twiss' not in f.filename,
            ))
    return res


# condensed version of https://github.com/radiasoft/rscon/blob/d3abdaf5c1c6d41797a4c96317e3c644b871d5dd/webcon/madx_examples/FODO_example_PTC.ipynb
def _ptc_particles(twiss_params, num_particles):
    mean = [0, 0, 0, 0]
    cov = []
    for dim in twiss_params:
        m1 = 1 if dim == 'x' else 0
        m2 = 1 - m1
        tp = PKDict(twiss_params[dim])
        dd = tp.beta * tp.emittance
        ddp = -tp.alpha * tp.emittance
        dpdp = tp.emittance * tp.gamma
        cov.append([m1 * dd, m1 * ddp, m2 * dd, m2 * ddp])
        cov.append([m1 * ddp, m1 * dpdp, m2 * ddp, m2 * dpdp])

    transverse = np.random.multivariate_normal(mean, cov, num_particles)
    x = transverse[:, 0]
    xp = transverse[:, 1]
    y = transverse[:, 2]
    yp = transverse[:, 3]

    # for now the longitudional coordinates are set to zero. This just means there
    # is no longitudinal distribuion. We can change this soon.
    long_part = np.random.multivariate_normal([0, 0], [[0, 0], [0, 0]], num_particles)

    particles = np.column_stack([x, xp, y, yp, long_part[:, 0], long_part[:, 1]])
    return PKDict(
        x=PKDict(pos=particles[:,0], p=particles[:,1]),
        y=PKDict(pos=particles[:,2], p=particles[:,3]),
        t=PKDict(pos=particles[:,4], p=particles[:,5]),
    )


def _ptc_start_commands(data):
    p = _ptc_particles(
        _get_initial_twiss_params(data),
        data.models.simulation.numberOfParticles
    )

    v = PKDict(
        x=p.x.pos,
        px=p.x.p,
        y=p.y.pos,
        py=p.y.p,
        t=p.t.pos,
        pt=p.t.p,
    )

    r = ''
    for i in range(len(v.x)):
        r += 'ptc_start'
        for f in ('x', 'px', 'y', 'py', 't', 'pt'):
           r += f', {f}={v[f][i]}'
        r +=';\n'
    return r


def _to_floats(values):
    return [float(v) for v in values]


def _twiss_ellipse_rotation(alpha, beta):
    if alpha == 0:
        return 0
    return 0.5 * math.atan(
        2. * alpha * beta / (1 + alpha * alpha - beta * beta)
    )
