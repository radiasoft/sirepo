# -*- coding: utf-8 -*-
u"""MAD-X execution template.

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern import pkcompat
from pykern import pkio
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdc, pkdlog
from sirepo import simulation_db
from sirepo.template import code_variable
from sirepo.template import lattice
from sirepo.template import madx_parser
from sirepo.template import particle_beam
from sirepo.template import template_common
from sirepo.template.lattice import LatticeUtil
import copy
import functools
import math
import numpy as np
import os.path
import pykern.pkinspect
import re
import scipy.constants
import sirepo.lib
import sirepo.sim_data


BUNCH_PARTICLES_FILE = 'ptc_particles.json'

MADX_INPUT_FILE = 'in.madx'

MADX_LOG_FILE = 'madx.log'

PTC_PARTICLES_FILE = 'ptc_particles.madx'

PTC_LAYOUT_COMMAND = 'ptc_create_layout'

_ALPHA_COLUMNS = ['name', 'keyword', 'parent', 'comments', 'number', 'turn', '']

_FIELD_UNITS = PKDict(
    betx='m',
    bety='m',
    dx='m',
    dy='m',
    mux='2π',
    muy='2π',
    s='m',
    x='m',
    y='m',
    x0='m',
    y0='m',
)

_PI = 4 * math.atan(1)

MADX_CONSTANTS = PKDict(
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

_OUTPUT_INFO_FILE = 'outputInfo.json'

_OUTPUT_INFO_VERSION = '1'

_END_MATCH_COMMAND = 'endmatch'

_PTC_TRACK_COMMAND = 'ptc_track'

_PTC_TRACKLINE_COMMAND = 'ptc_trackline'

_SIM_DATA, SIM_TYPE, SCHEMA = sirepo.sim_data.template_globals()

PTC_OBSERVE_TWISS_COLS = [
    'W',
    'alfx',
    'alfy',
    'betx',
    'bety',
    'ct0',
    'ctct',
    'ctpt',
    'emit_t',
    'emit_x',
    'emit_y',
    'eta_px',
    'eta_py',
    'eta_x',
    'eta_y',
    'gamma_x',
    'gamma_y',
    'n',
    'pt0',
    'ptpt',
    'px0',
    'pxct',
    'pxpt',
    'pxpx',
    'pxpy',
    'pxy',
    'py0',
    'pyct',
    'pypt',
    'pypy',
    's',
    'x0',
    'xct',
    'xpt',
    'xpx',
    'xpy',
    'xx',
    'xy',
    'y0',
    'yct',
    'ypt',
    'ypy',
    'yy',
]


_TFS_FILE_EXTENSION = 'tfs'

_TWISS_OUTPUT_FILE = f'twiss.{_TFS_FILE_EXTENSION}'

#TODO(pjm): this is only a start on the MAD-X LibAdapter
class LibAdapter(sirepo.lib.LibAdapterBase):

    def parse_file(self, path):
        from sirepo.template import madx_parser
        return self._convert(madx_parser.parse_file(pkio.read_text(path)))

    def write_files(self, data, source_path, dest_dir):
        """writes files for the simulation

        Returns:
            PKDict: structure of files written (debugging only)
        """
        pkio.write_text(
            dest_dir.join(source_path.basename),
            generate_parameters_file(data),
        )
        if LatticeUtil.find_first_command(data, PTC_LAYOUT_COMMAND):
            import sirepo.pkcli.madx
            #TODO(pjm): move the method to template.madx.generate_ptc_particles_file()
            sirepo.pkcli.madx._generate_ptc_particles_file(dest_dir, data, None)
        return PKDict()


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
            k = LatticeUtil.file_id(model._id, self.field_index)
            self.result[k] = PKDict(
                filename=b + f'.{_TFS_FILE_EXTENSION}',
                model_type=model._type,
                purebasename=b,
                ext=_TFS_FILE_EXTENSION,
            )
            self.result.keys_in_order.append(k)

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


def code_var(variables):
    return code_variable.CodeVar(
        variables,
        code_variable.PurePythonEval(MADX_CONSTANTS),
        case_insensitive=True,
    )

def eval_code_var(data):
    # TODO(e-carlin): When #3111 is merged use the code in LibAdapterBase._convert
    # to do this work. It is copied from there.
    cv = code_var(data.models.rpnVariables)

    def _model(model, name):
        schema = SCHEMA.model[name]

        k = x = v = None
        try:
            for k, x in schema.items():
                t = x[1]
                v = model[k] if k in model else x[2]
                if t == 'RPNValue':
                    t = 'Float'
                    if cv.is_var_value(v):
                        model[k] = cv.eval_var_with_assert(v)
                        continue
                if t == 'Float':
                    model[k] = float(v) if v else 0.
                elif t == 'Integer':
                    model[k] = int(v) if v else 0
        except Exception as e:
            pkdlog('model={} field={} decl={} value={} exception={}', name, k, x, v, e)
            raise

    for x in  data.models.rpnVariables:
        x.value = cv.eval_var_with_assert(x.value)
    for k, v in data.models.items():
        if k in SCHEMA.model:
            _model(v, k)
    for x in ('elements', 'commands'):
        for m in data.models[x]:
            _model(m, LatticeUtil.model_name_for_data(m))


def extract_parameter_report(data, run_dir=None, filename=_TWISS_OUTPUT_FILE, results=None):
    if not results:
        assert run_dir and filename, \
            f'must supply either results or run_dir={run_dir} and filename={filename}'
    t = results or madx_parser.parse_tfs_file(run_dir.join(filename))
    plots = []
    m = data.models[data.report]
    for f in ('y1', 'y2', 'y3'):
        if m[f] == 'None':
            continue
        if m[f] not in t:
            return PKDict(
                error=f'Missing column "{m[f]}" in report output file.',
            )
        plots.append(
            PKDict(field=m[f], points=to_floats(t[m[f]]), label=field_label(m[f])),
        )
    x = m.get('x', 's')
    res = template_common.parameter_plot(
        to_floats(t[x]),
        plots,
        m,
        PKDict(
            y_label='',
            x_label=field_label(x),
            dynamicYLabel=True,
        )
    )
    if filename == _TWISS_OUTPUT_FILE and not results:
        res.initialTwissParameters = PKDict(
            betx=t.betx[0],
            bety=t.bety[0],
            alfx=t.alfx[0],
            alfy=t.alfy[0],
            x=t.x[0],
            y=t.y[0],
            px=t.px[0],
            py=t.py[0],
        )
    return res


def generate_parameters_file(data):
    res, v = template_common.generate_parameters_file(data)
    if data.models.simulation.computeTwissFromParticles == '1':
        _add_marker_and_observe(data)
    util = LatticeUtil(data, SCHEMA)
    filename_map = _build_filename_map_from_util(util)
    report = data.get('report', '')
    v.twissOutputFilename = _TWISS_OUTPUT_FILE
    v.lattice = _generate_lattice(filename_map, util)
    v.variables = code_var(data.models.rpnVariables).generate_variables(_generate_variable)
    v.useBeamline = util.select_beamline().name
    if report == 'twissReport' or _is_report('bunchReport', report):
        v.twissOutputFilename = _TWISS_OUTPUT_FILE
        return template_common.render_jinja(SIM_TYPE, v, 'twiss.madx')
    _add_commands(data, util)

    pkdp('\n\n\n busted data.models.commands: {}', data.models.commands)
    pkdp('\n\n\n busted data.models.bunch: {}', data.models.bunch)

    beam = LatticeUtil.find_first_command(data, 'beam')
    for k in data.models.bunch:
        v = data.models.bunch[k]
        if type(v) == str and 'pow' in v:
            data.models.bunch[k] = eval(v)
    for k in beam:
        v = beam[k]
        if type(v) == str and 'pow' in v:
            beam[k] = eval(v)

    for i, c in enumerate(data.models.commands):
        if c._id == beam._id:
            data.models.commands[i] = beam

    pkdp('\n\n\n fixed data.models.commands: {}', data.models.commands)
    pkdp('\n\n\n fixed data.models.bunch: {}', data.models.bunch)


    v.commands = _generate_commands(filename_map, util)
    v.hasTwiss = bool(util.find_first_command(data, 'twiss'))
    if not v.hasTwiss:
        v.twissOutputFilename = _TWISS_OUTPUT_FILE
    return template_common.render_jinja(SIM_TYPE, v, 'parameters.madx')


def get_data_file(run_dir, model, frame, options=None, **kwargs):
    if frame == SCHEMA.constants.logFileFrameId:
        return template_common.text_data_file(MADX_LOG_FILE, run_dir)
    if frame >= 0:
        data = simulation_db.read_json(run_dir.join(template_common.INPUT_BASE_NAME))
        if model == 'twissFromParticlesAnimation':
            return [
                f.filename for f in _build_filename_map(data).values() \
                if hasattr(f, 'get') and f.get('model_type') == _PTC_TRACK_COMMAND
            ][-1]
        return _get_filename_for_element_id(
            re.sub(r'elementAnimation', '', model),
            data,
        ).filename
    if _is_report('bunchReport', model):
        return PTC_PARTICLES_FILE
    assert False, f'no data file for model: {model}'


def import_file(req, **kwargs):
    text = pkcompat.from_bytes(req.file_stream.read())
    if not bool(re.search(r'\.madx$|\.seq$', req.filename, re.IGNORECASE)):
        raise AssertionError('invalid file extension, expecting .madx or .seq')
    data = madx_parser.parse_file(text, downcase_variables=True)
    # TODO(e-carlin): need to clean this up. copied from elegant
    data.models.simulation.name = re.sub(
        r'\.madx$|\.seq$',
        '',
        req.filename,
        flags=re.IGNORECASE
    )
    return data


def post_execution_processing(success_exit=True, run_dir=None, **kwargs):
    if success_exit:
        return None
    return _parse_madx_log(run_dir)


def prepare_for_client(data):
    code_var(data.models.rpnVariables).compute_cache(data, SCHEMA)
    return data


def prepare_sequential_output_file(run_dir, data):
    r = data.report
    if r == 'twissReport' or _is_report('bunchReport', r) or _is_report('twissEllipseReport', r):
        f = simulation_db.json_filename(template_common.OUTPUT_BASE_NAME, run_dir)
        if f.exists():
            f.remove()
            try:
                save_sequential_report_data(data, run_dir)
            except IOError:
                # the output file isn't readable
                pass


# TODO(e-carlin): fixme - I don't return python
def python_source_for_model(data, model):
    return generate_parameters_file(data)


def sim_frame(frame_args):
    d = frame_args.sim_in
    d.report = frame_args.frameReport
    d.models[d.report] = frame_args
    return _extract_report_data(d, frame_args.run_dir)


def save_sequential_report_data(data, run_dir):
    template_common.write_sequential_result(
        _extract_report_data(data, run_dir),
        run_dir=run_dir,
    )


def stateless_compute_calculate_bunch_parameters(data):
    return _calc_bunch_parameters(data.bunch, data.command_beam, data.variables)


def to_float(value):
    return float(value)


def to_floats(values):
    return [to_float(v) for v in values]


def to_string(value):
    return value.replace('"', '')


def uniquify_elements(data):
    def _do_unique(elem_ids):
        element_map = PKDict({e._id: e for e in data.models.elements})
        names = set([e.name for e in data.models.elements])
        max_id = LatticeUtil.max_id(data)
        res = []
        for el_id in elem_ids:
            if el_id not in res:
                res.append(el_id)
                continue
            el = copy.deepcopy(element_map[el_id])
            el.name = _unique_name(el.name, names)
            max_id += 1
            el._id = max_id
            data.models.elements.append(el)
            res.append(el._id)
        return res

    def _insert_items(old_items, new_items, beamline, index):
        beamline['items'] = old_items[:index] + \
            new_items + old_items[index + 1:]

    def _reflect_children(id_to_reflect, index, beamline, reflecting_grandchildren=False):
        if abs(id_to_reflect) not in beamline_map:
            # It is an element, we're done.
            return
        if id_to_reflect < 0 and reflecting_grandchildren:
            # TODO(e-carlin): This is may be wrong. The manual says "Sub-lines
            # of reflected lines are also reflected" but, it doesn't say if a
            # sub-line of the sub-line is itself reflected then the reflections
            # cancel eachother out. It seems to work but could be wrong.
            beamline['items'][index] = abs(id_to_reflect)
            return
        n = beamline_map[abs(id_to_reflect)]['items'].copy()
        n.reverse()
        _insert_items(beamline['items'], n, beamline_map[beamline.id], index)
        for i, e in enumerate(n):
            _reflect_children(e, index + i, b, reflecting_grandchildren=True)

    def _reduce_to_elements_with_reflection(beamline):
        """Reduce a beamline to just elements while reflecting negative sub-lines

        An item that is negative means it and all of it's sublines
        need to be reflected (reverse the order of elements).
        Manual section on "Reflection and Repetition":
        https://mad.web.cern.ch/mad/webguide/manual.html#Ch13.S3
        """
        for i, e in enumerate(beamline['items'].copy()):
            if e >= 0:
                if e in beamline_map:
                    _insert_items(
                        beamline['items'],
                        beamline_map[e]['items'],
                        beamline,
                        i,
                    )
                    break
                continue
            _reflect_children(e, i, beamline)
            break
        else:
            return
        # Need to start over because items have changed out from underneath us
        _reduce_to_elements_with_reflection(beamline_map[data.models.simulation.visualizationBeamlineId])

    def _remove_unused_elements(items):
        res = []
        for el in data.models.elements:
            if el._id in items:
                res.append(el)
        data.models.elements = res

    def _unique_name(name, names):
        assert name in names
        count = 2
        m = re.search(r'(\d+)$', name)
        if m:
            count = int(m.group(1))
            name = re.sub(r'\d+$', '', name)
        while f'{name}{count}' in names:
            count += 1
        names.add(f'{name}{count}')
        return f'{name}{count}'

    beamline_map = PKDict({
        b.id: b for b in data.models.beamlines
    })
    b = beamline_map[data.models.simulation.visualizationBeamlineId]
    _reduce_to_elements_with_reflection(b)
    _remove_unused_elements(b['items'])
    b['items'] = _do_unique(b['items'])
    data.models.beamlines = [b]


def write_parameters(data, run_dir, is_parallel, filename=MADX_INPUT_FILE):
    """Write the parameters file

    Args:
        data (dict): input
        run_dir (py.path): where to write
        is_parallel (bool): run in background?
    """
    if _is_report('twissEllipseReport', data.report) or _is_report('bunchReport', data.report):
        # these reports don't need to run madx
        return
    pkio.write_text(
        run_dir.join(filename),
        # generate_parameters_file may modify data and pkcli.madx may call
        # write_parameters multiple times so make a copy
        generate_parameters_file(copy.deepcopy(data)),
    )


def _add_commands(data, util):
    commands = data.models.commands
    # set the selected beamline depending on the lattice or visualization
    idx = next(i for i, cmd in enumerate(commands) if cmd._type == 'beam')
    commands.insert(idx + 1, PKDict(
        _type='use',
        sequence=util.select_beamline().id,
        _id=LatticeUtil.max_id(data),
    ))
    if not util.find_first_command(data, PTC_LAYOUT_COMMAND):
        return
    # insert call for particles after ptc_create_layout
    idx = next(i for i, cmd in enumerate(commands) if cmd._type == PTC_LAYOUT_COMMAND)
    commands.insert(idx + 1, PKDict(
        _type='call',
        file=PTC_PARTICLES_FILE,
        _id=LatticeUtil.max_id(data),
    ))



def _add_marker_and_observe(data):
    def _add_marker(data):
        assert len(data.models.beamlines) == 1, \
            f'should have only one beamline reduced to elements. beamlines={data.models.beamlines}'
        beam = data.models.beamlines[0]
        markers = PKDict()
        m = LatticeUtil.max_id(data)
        el_map = PKDict()
        for el in data.models.elements:
            el_map[el._id] = el
        items_copy = beam['items'].copy()
        bi = 0
        for i, v in enumerate(items_copy):
            bi += 1
            el = el_map[items_copy[i]]
            if el.type == 'INSTRUMENT' or 'MONITOR' in el.type:
                # always include instrument and monitor positions
                pass
            elif not el.get('l', 0):
                continue
            m += 1
            beam['items'].insert(bi, m)
            bi += 1
            n = f'Marker{m}_{el.type}'
            markers[m] = n
            data.models.elements.append(PKDict(
                _id=m,
                name=n,
                type='MARKER',
            ))
        return markers, m

    def _add_ptc_observe(markers, max_id):
        for i, c in enumerate(data.models.commands):
            if c._type == 'ptc_create_universe':
                break
        else:
            raise AssertionError(
                f'no ptc_create_universe command found in commands={data.models.commands}',
            )
        d = max_id
        for m in markers.values():
            d += 1
            data.models.commands.insert(i + 1, PKDict(
                _id=d,
                _type='ptc_observe',
                place=m,
            ))

    uniquify_elements(data)
    _add_ptc_observe(*_add_marker(data))


def _build_filename_map(data):
    return _build_filename_map_from_util(LatticeUtil(data, SCHEMA))


def _build_filename_map_from_util(util):
    return util.iterate_models(MadxOutputFileIterator()).result


def _calc_bunch_parameters(bunch, beam, variables):
    try:
        field = bunch.beamDefinition
        cv = code_var(variables)
        energy = template_common.ParticleEnergy.compute_energy(
            SIM_TYPE,
            beam.particle,
            PKDict({
                'mass': cv.eval_var_with_assert(beam.mass),
                'charge': cv.eval_var_with_assert(beam.charge),
                field: cv.eval_var_with_assert(beam[field]),
            }),
        )
        for f in energy:
            # don't overwrite mass or charge
            if f in ('mass', 'charge'):
                continue
            if f in beam and f != field:
                beam[f] = energy[f]
    except AssertionError:
        pass
    return PKDict(command_beam=beam)


def _extract_report_bunchReport(data, run_dir):
    parts = simulation_db.read_json(run_dir.join(BUNCH_PARTICLES_FILE))
    m = data.models[data.report]
    res = template_common.heatmap(
        [
            parts[m.x],
            parts[m.y],
        ],
        m,
        PKDict(
            x_label=field_label(m.x),
            y_label=field_label(m.y),
        )
    )
    bunch = data.models.bunch
    res.summaryData = parts.summaryData
    return res


def _extract_report_data(data, run_dir):
    r = data.report
    m = re.split(r'(\d+)', r)
    f = getattr(
        pykern.pkinspect.this_module(),
        '_extract_report_' + m[0] if m else r
    )
    f = functools.partial(f, data, run_dir)
    if 'Animation' in r:
        f = functools.partial(f, filename=_filename_for_report(run_dir, r))
    return f()


def _extract_report_elementAnimation(data, run_dir, filename):
    if is_parameter_report_file(filename):
        return extract_parameter_report(data, run_dir, filename)
    m = data.models[data.report]
    t = madx_parser.parse_tfs_file(run_dir.join(filename), want_page=m.frameIndex)
    info = madx_parser.parse_tfs_page_info(run_dir.join(filename))[m.frameIndex]

    return template_common.heatmap(
        [to_floats(t[m.x]), to_floats(t[m.y1])],
        m,
        PKDict(
            x_label=field_label(m.x),
            y_label=field_label(m.y1),
            title='{}-{} at {}m, {} turn {}'.format(
                m.x, m.y1, info.s, info.name, info.turn,
            ),
        ),
    )


def _extract_report_matchSummaryAnimation(data, run_dir, filename):
    return PKDict(
        summaryText=_parse_match_summary(run_dir, filename),
    )


def _extract_report_twissEllipseReport(data, run_dir):
    #TODO(pjm): use bunch twiss values, not command_twiss values
    beam = _first_beam_command(data)
    r_model = data.models[data.report]
    dim = r_model.dim
    n_pts = 100
    theta = np.arange(0, 2. * np.pi * (n_pts / (n_pts - 1)), 2. * np.pi / n_pts)
    #TODO(pjm): get code_var value for alf, bet, d
    a = float(data.models.bunch[f'alf{dim}']) or 0
    b = float(data.models.bunch[f'bet{dim}']) or 0
    assert b > 0, f'TWISS parameter "bet{dim}" must be > 0'
    g = (1. + a * a) / b
    e = (beam[f'e{dim}'] or 1)
    phi = _twiss_ellipse_rotation(a, b)

    # major, minor axes of ellipse
    mj = np.sqrt(e * b)
    mn = np.sqrt(e * g)

    # apply rotation
    x = mj * np.cos(theta) * np.sin(phi) + mn * np.sin(theta) * np.cos(phi)
    y = mj * np.cos(theta) * np.cos(phi) - mn * np.sin(theta) * np.sin(phi)

    return template_common.parameter_plot(
        x.tolist(),
        [PKDict(field=dim, points=y.tolist(), label=f'{dim}\' [rad]')],
        {},
        PKDict(
            title=f'a{dim} = {a} b{dim} = {b} g{dim} = {g}',
            y_label='',
            x_label=f'{dim} [m]'
        )
    )


def extract_report_twissFromParticlesAnimation(data, run_dir, filename):
    res = particle_beam.analyze_ptc_beam(
        particle_beam.read_ptc_data(run_dir.join(filename))[0],
        mc2=SCHEMA.constants.particleMassAndCharge.proton[0],
    )
    # remap alpha/beta columns
    for dim in ('x', 'y'):
        res[f'alf{dim}'] = res[f'alpha_{dim}']
        del res[f'alpha_{dim}']
        res[f'bet{dim}'] = res[f'beta_{dim}']
        del res[f'beta_{dim}']
    assert set(res.keys()) == set(PTC_OBSERVE_TWISS_COLS), \
        f'unknown ptc twiss columns={set(res.keys())} expected={PTC_OBSERVE_TWISS_COLS}'
    return extract_parameter_report(
        data,
        results=PKDict(res),
    )

def _extract_report_twissFromParticlesAnimation(data, run_dir, filename):
    return extract_report_twissFromParticlesAnimation(data, run_dir, filename)


def _extract_report_twissReport(data, run_dir):
    return extract_parameter_report(data, run_dir)


def field_label(field):
    if field in _FIELD_UNITS:
        return '{} [{}]'.format(field, _FIELD_UNITS[field])
    return field


def file_info(filename, run_dir, file_id):
    path = str(run_dir.join(filename))
    plottable = []
    tfs = madx_parser.parse_tfs_file(path)
    for f in tfs:
        if f in _ALPHA_COLUMNS:
            continue
        v = to_floats(tfs[f])
        if np.any(v):
            plottable.append(f)
    count = 1
    if 'turn' in tfs:
        info = madx_parser.parse_tfs_page_info(path)
        count = len(info)
    return PKDict(
        modelKey='elementAnimation{}'.format(file_id),
        filename=filename,
        isHistogram=not is_parameter_report_file(filename),
        plottableColumns=plottable,
        pageCount=count,
    )


def _filename_for_report(run_dir, report):
    for info in _output_info(run_dir):
        if info.modelKey == report:
            return info.filename
    if report == 'matchSummaryAnimation':
        return MADX_LOG_FILE
    assert False, f'no output file for report={report}'


def first_beam_command(data):
    return _first_beam_command(data)


def _first_beam_command(data):
    m = LatticeUtil.find_first_command(data, 'beam')
    assert m, 'BEAM missing from command list'
    return m


def _format_field_value(state, model, field, el_type):
    v = model[field]
    if el_type == 'Boolean' or el_type == 'OptionalBoolean':
        v = 'true' if v == '1' else 'false'
    elif 'LatticeBeamlineList' in el_type:
        v = state.id_map[int(v)].name
    elif el_type == 'OutputFile':
        v = '"{}"'.format(state.filename_map[LatticeUtil.file_id(model._id, state.field_index)].filename)
    elif el_type == 'RPNValue':
        v = _format_rpn_value(v)
    return [field, v]


def _format_rpn_value(value):
    import astunparse
    import ast
    class Visitor(ast.NodeTransformer):
        def visit_Call(self, node):
            if node.func.id == 'pow':
                return ast.BinOp(
                    left=node.args[0],
                    op=ast.Pow(),
                    right=node.args[1],
                    keywords=[]
                )
            return node
    r = code_variable.PurePythonEval.postfix_to_infix(value)
    if type(r) == str and 'pow' in r:
        tree = ast.parse(r)
        for n in ast.walk(tree):
            Visitor().visit(n)
            ast.fix_missing_locations(n)
        r = astunparse.unparse(tree).strip().replace('**', '^')
    return r

def _generate_commands(filename_map, util):
    _update_beam_energy(util.data)
    for c in util.data.models.commands:
        if c._type in (_PTC_TRACK_COMMAND, _PTC_TRACKLINE_COMMAND):
            c.onetable = '1'
        if c._type == _PTC_TRACK_COMMAND and \
           int(util.data.models.simulation.computeTwissFromParticles) and \
           int(c.icase) == 4:
            raise AssertionError(
                f'ptc_track.icase must be set to 5 or 6 to compute twiss from particles',
            )
    res = util.render_lattice(
        util.iterate_models(
            lattice.ElementIterator(filename_map, _format_field_value),
            'commands',
        ).result,
        want_semicolon=True,
        want_name=False,
    )
    return res


def _generate_lattice(filename_map, util):
    return util.render_lattice_and_beamline(
        lattice.LatticeIterator(filename_map, _format_field_value),
        want_semicolon=True,
        want_var_assign=True,
        madx_name=True,
    )


def _generate_variable(name, variables, visited):
    res = ''
    if name not in visited:
        res += 'REAL {} = {};\n'.format(name, _format_rpn_value(variables[name]))
        visited[name] = True
    return res


def _get_filename_for_element_id(file_id, data):
    return _build_filename_map(data)[file_id]


def is_parameter_report_file(filename):
    return 'twiss' in filename or 'touschek' in filename


def _is_report(name, report):
    return name in report


def _output_info(run_dir):
    # cache outputInfo to file, used later for report frames
    info_file = run_dir.join(_OUTPUT_INFO_FILE)
    if os.path.isfile(str(info_file)):
        try:
            res = simulation_db.read_json(info_file)
            if not res or res[0].get('_version', '') == _OUTPUT_INFO_VERSION:
                return res
        except ValueError as e:
            pass
    data = simulation_db.read_json(run_dir.join(template_common.INPUT_BASE_NAME))
    files = _build_filename_map(data)
    res = []
    for k in files.keys_in_order:
        f = files[k]
        if run_dir.join(f.filename).exists():
            res.append(file_info(f.filename, run_dir, k))
            if f.model_type == _PTC_TRACK_COMMAND and \
               int(data.models.simulation.computeTwissFromParticles):
                res.insert(0, PKDict(
                    modelKey='twissFromParticlesAnimation',
                    filename=f.filename,
                    isHistogram=True,
                    plottableColumns=PTC_OBSERVE_TWISS_COLS,
                    pageCount=0,
                ))
    if LatticeUtil.find_first_command(data, _END_MATCH_COMMAND):
        res.insert(0, PKDict(
            modelKey='matchAnimation',
            filename='madx.log',
            isHistogram=False,
            plottableColumns=[],
            pageCount=0,
        ))
    if res:
        res[0]['_version'] = _OUTPUT_INFO_VERSION
    simulation_db.write_json(info_file, res)
    return res


def _parse_madx_log(run_dir):
    path = run_dir.join(MADX_LOG_FILE)
    if not path.exists():
        return ''
    res = ''
    with pkio.open_text(str(path)) as f:
        for line in f:
            if re.search(r'^\++ (error|warning):', line, re.IGNORECASE):
                line = re.sub(r'^\++ ', '', line)
                res += line + "\n"
            elif re.search(r'^\+.*? fatal:', line, re.IGNORECASE):
                line = re.sub(r'^.*? ', '', line)
                res += line + "\n"
    return res


def _parse_match_summary(run_dir, filename):
    path = run_dir.join(filename)
    node_names = ''
    res = ''
    with pkio.open_text(str(path)) as f:
        state = 'search'
        for line in f:
            if re.search(r'^MATCH SUMMARY', line):
                state = 'summary'
            elif state == 'summary':
                if re.search(r'^END MATCH SUMMARY', line):
                    state = 'node_names'
                else:
                    res += line
            elif state == 'node_names':
                # MAD-X formats the outpus incorrectly when piped to a file
                # need to look after the END MATCH for node names
                #Global constraint:         dq1          4     0.00000000E+00    -3.04197881E-12     9.25363506E-24
                if len(line) > 28 and re.search(r'^\w.*?\:', line) and line[26] == ' ' and line[27] != ' ':
                    node_names += line
    if node_names:
        res = re.sub(r'(Node_Name .*?\n\-+\n)', r'\1' + node_names, res)
    return res


def _twiss_ellipse_rotation(alpha, beta):
    if alpha == 0:
        return 0
    return 0.5 * math.atan(
        2. * alpha * beta / (1 + alpha * alpha - beta * beta)
    )


def _update_beam_energy(data):
    beam = _first_beam_command(data)
    bunch = data.models.bunch
    if bunch.beamDefinition != 'other':
        for e in SCHEMA.enum.BeamDefinition:
            if bunch.beamDefinition != e[0]:
                beam[e[0]] = 0
