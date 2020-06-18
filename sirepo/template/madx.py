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
import math
import numpy as np
import pykern.pkinspect
import re
import scipy.constants
import sirepo.sim_data


MADX_INPUT_FILE = 'madx.in'

MADX_OUTPUT_FILE = 'madx.out'

_FILE_TYPES = ['ele', 'lte', 'madx']
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

_MADX_PTC_PARTICLES_FILE = 'ptc_particles.madx'

_MADX_PTC_TRACK_DUMP_FILE = 'ptc_track_dump'

_MADX_PTC_TRACK_DUMP_FILE_EXTENSION = 'tfs'

_MADX_TWISS_OUTPUT_FILE = 'twiss.tfs'

_METHODS = template_common.RPN_METHODS + []

_SIM_DATA, SIM_TYPE, _SCHEMA = sirepo.sim_data.template_globals()



def background_percent_complete(report, run_dir, is_running):
    if is_running:
        return PKDict(
            percentComplete=0,
            frameCount=0,
        )
    return PKDict(
        percentComplete=100,
        frameCount=1,
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


# TODO(e-carlin): need to clean this up. copied from elegant
# ex _map_commands_to_lattice doesn't exist in this file only in elegant
def import_file(req, test_data=None, **kwargs):
    ft = '|'.join(_FILE_TYPES)
    if not re.search(r'\.({})$'.format(ft), req.filename, re.IGNORECASE):
        raise IOError('invalid file extension, expecting one of {}'.format(_FILE_TYPES))
    # input_data is passed by test cases only
    input_data = test_data
    text = pkcompat.from_bytes(req.file_stream.read())
    if 'simulationId' in req.req_data:
        input_data = simulation_db.read_simulation_json(SIM_TYPE, sid=req.req_data.simulationId)
    if re.search(r'\.ele$', req.filename, re.IGNORECASE):
        data = elegant_command_importer.import_file(text)
    elif re.search(r'\.lte$', req.filename, re.IGNORECASE):
        data = elegant_lattice_importer.import_file(text, input_data)
        if input_data:
            _map_commands_to_lattice(data)
    elif re.search(r'\.madx$', req.filename, re.IGNORECASE):
        data = madx_parser.parse_file(text, downcase_variables=True)
        madx_converter.fixup_madx(data)
    else:
        raise IOError('invalid file extension, expecting .ele or .lte')
    data.models.simulation.name = re.sub(
        r'\.({})$'.format(ft),
        '',
        req.filename,
        flags=re.IGNORECASE
    )
    if input_data and not test_data:
        simulation_db.delete_simulation(
            SIM_TYPE,
            input_data.models.simulation.simulationId
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
    m = d.models[d.report]
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
        run_dir.join(_MADX_PTC_PARTICLES_FILE),
        _generate_ptc_particles_file(data),
    )
    pkio.write_text(
        run_dir.join(MADX_INPUT_FILE),
        _generate_parameters_file(data),
    )


def _add_call_and_observe_commands(data, util):
    commands = data.models.commands
    # set the selected beamline depending on the lattice or visualization
    idx = next(i for i, cmd in enumerate(commands) if cmd._type == 'beam')
    commands.insert(idx + 1, PKDict(
        _type='use',
        sequence=util.select_beamline().id,
    ))
    # insert call and ptc_observe commands after ptc_create_layout
    idx = next(i for i, cmd in enumerate(commands) if cmd._type == 'ptc_create_layout')
    commands.insert(idx + 1, PKDict(
        _type='call',
        file=_MADX_PTC_PARTICLES_FILE,
    ))
    commands.insert(idx + 2, PKDict(
        _type='ptc_observe',
        place='{}$END'.format(util.select_beamline().name.upper()),
    ))


def _code_var(variables):
    return code_variable.CodeVar(
        variables,
        code_variable.PurePythonEval(_MADX_CONSTANTS),
        case_insensitive=True,
    )


def _extract_report_data(data, run_dir):
    r = data.get('report', data.get('frameReport'))
    if 'twissEllipse' in r:
        return _extract_report_twissEllipseReport(data, run_dir)
    elif 'bunchReport' in data.report:
        return _extract_report_bunchReport(data, run_dir)
    elif r.startswith('twiss'):
        return _extract_report_twissReport(data, run_dir)
    return getattr(
        pykern.pkinspect.this_module(),
        '_extract_report_' + r,
    )(data, run_dir)


def _extract_report_bunchReport(data, run_dir):
    util = LatticeUtil(data, _SCHEMA)
    m = util.find_first_command(data, 'twiss')
    if not m:
        return template_common.parameter_plot([], [], None, PKDict())
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


def _twiss_ellipse_rotation(alpha, beta):
    if alpha == 0:
        return 0
    return 0.5 * math.atan(
        2. * alpha * beta / (1 + alpha * alpha - beta * beta)
    )


def _get_initial_twiss_params(data):
    p = PKDict(
        x=PKDict(),
        y=PKDict()
    )
    util = LatticeUtil(data, _SCHEMA)
    m = util.find_first_command(data, 'twiss')
    # must an initial twiss always exist?
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


def _extract_report_ptcAnimation(data, run_dir):
    m = data.models[data.report]
    t = madx_parser.parse_tfs_file(
        run_dir.join(
            # POSIT: We are using the onetable option so madx appends one to the filename
            f'{_MADX_PTC_TRACK_DUMP_FILE}one.{_MADX_PTC_TRACK_DUMP_FILE_EXTENSION}',
        ),
    )
    return template_common.heatmap(
        [_to_floats(t[m.x]), _to_floats(t[m.y])],
        m,
        PKDict(
            x_label=_FIELD_LABEL[m.x],
            y_label=_FIELD_LABEL[m.y],
            title=data.models.simulation.name,
        ),
    )


def _extract_report_twissReport(data, run_dir):
    t = madx_parser.parse_tfs_file(run_dir.join(_MADX_TWISS_OUTPUT_FILE))
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


def _format_field_value(state, model, field, el_type):
    v = model[field]
    if el_type == 'Boolean':
        v = 'true' if v == '1' else 'false'
    elif el_type == 'LatticeBeamlineList':
        v = state.id_map[int(v)].name
    return [field, v]


def _generate_commands(util):
    res = ''
    for c in util.iterate_models(
            lattice.ElementIterator(None, _format_field_value), 'commands'
    ).result:
        res += f'{c[0]._type}'
        for f in c[1]:
           res += f', {f[0]}={f[1]}'
        t = c[0]._type
        if t == 'twiss':
            res += f', file={_MADX_TWISS_OUTPUT_FILE}'
        elif t == 'ptc_track':
            res += (f', dump=true, onetable=true file={_MADX_PTC_TRACK_DUMP_FILE}'
                    f', extension=.{_MADX_PTC_TRACK_DUMP_FILE_EXTENSION}')
        # elif t == 'call':
        #     res += f', file={_MADX_PTC_PARTICLES_FILE}'
        res += ';\n'
    return res


def _generate_lattice(util):
    filename_map = PKDict()
    return util.render_lattice_and_beamline(
        lattice.LatticeIterator(filename_map, _format_field_value),
        want_semicolon=True)


def _generate_parameters_file(data):
    res, v = template_common.generate_parameters_file(data)

    v.report = re.sub(r'\d+$', '', data.report)
    if v.report in _INITIAL_REPORTS:
        # these reports do not require running madx first
        v.initialTwissParameters = _get_initial_twiss_params(data)
        v.numParticles = data.models.particleTracking.numParticles
        v.particleFile = simulation_db.simulation_dir(SIM_TYPE, data.simulationId) \
            .join(data.report).join('ptc_particles.txt')
        res = template_common.render_jinja(SIM_TYPE, v, 'bunch.py')
        return res

    util = LatticeUtil(data, _SCHEMA)
    report = data.get('report', '')
    code_var = _code_var(data.models.rpnVariables)
    v.twissOutputFilename = _MADX_TWISS_OUTPUT_FILE
    v.lattice = _generate_lattice(util)
    v.variables = _generate_variables(code_var, data)

    v.useBeamline = util.select_beamline().name
    if report == 'twissReport':
        v.twissOutputFilename = _MADX_TWISS_OUTPUT_FILE
        return template_common.render_jinja(SIM_TYPE, v, 'twiss.madx')
    _add_call_and_observe_commands(data, util)
    v.commands = _generate_commands(util)
    v.hasTwiss = bool(util.find_first_command(data, 'twiss'))
    if not v.hasTwiss:
        v.twissOutputFilename = _MADX_TWISS_OUTPUT_FILE
    return template_common.render_jinja(SIM_TYPE, v, 'parameters.madx')


def _generate_ptc_particles_file(data):
    return template_common.render_jinja(
        SIM_TYPE,
        PKDict(start_commands=_ptc_start_commands(data)),
        _MADX_PTC_PARTICLES_FILE,
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


def _format_field_value(state, model, field, el_type):
    v = model[field]
    if el_type == 'Boolean':
        v = 'true' if v == '1' else 'false'
    elif el_type == 'LatticeBeamlineList':
        v = state.id_map[int(v)].name
    return [field, v]


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
