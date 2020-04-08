# -*- coding: utf-8 -*-
u"""Synergia execution template.

:copyright: Copyright (c) 2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkio
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdp, pkdlog
from sirepo import simulation_db
from sirepo.srschema import get_enums
from sirepo.template import lattice
from sirepo.template import template_common
from sirepo.template.lattice import LatticeUtil
from synergia import foundation
import glob
import h5py
import math
import py.path
import re
import sirepo.sim_data
import sirepo.util
import werkzeug


_SIM_DATA, SIM_TYPE, _SCHEMA = sirepo.sim_data.template_globals()

OUTPUT_FILE = PKDict(
    bunchReport='particles.h5',
    twissReport='twiss.h5',
    twissReport2='twiss.h5',
    beamEvolutionAnimation='diagnostics.h5',
    turnComparisonAnimation='diagnostics.h5',
)

WANT_BROWSER_FRAME_CACHE = True

_COORD6 = ['x', 'xp', 'y', 'yp', 'z', 'zp']

_FILE_ID_SEP = '-'

_IGNORE_ATTRIBUTES = ['lrad']

_QUOTED_MADX_FIELD = ['ExtractorType', 'Propagator']

_UNITS = PKDict(
    x='m',
    y='m',
    z='m',
    xp='rad',
    yp='rad',
    zp='rad',
    cdt='m',
    xstd='m',
    ystd='m',
    zstd='m',
    xmean='m',
    ymean='m',
    zmean='m',
    beta_x='m',
    beta_y='m',
    psi_x='rad',
    psi_y='rad',
    D_x='m',
    D_y='m',
    Dprime_x='rad',
    Dprime_y='rad',
)

class SynergiaLatticeIterator(lattice.LatticeIterator):
    def __init__(self, formatter):
        lattice.LatticeIterator.__init__(self, None, formatter)

    def end(self, model):
        if model.type == 'NLINSERT':
            # show the NLINSERT as a comment and explode the actual elements
            self.result.append([
                PKDict(
                    name='! {}'.format(model.name),
                    type='NLINSERT',
                ),
                self.fields,
            ])
            self.result += _nlinsert_field_values(model, self.id_map)
        else:
            super(SynergiaLatticeIterator, self).end(model)


def background_percent_complete(report, run_dir, is_running):
    diag_file = run_dir.join(OUTPUT_FILE.beamEvolutionAnimation)
    if diag_file.exists():
        particle_file_count = len(_particle_file_list(run_dir))
        # if is_running:
        #     particle_file_count -= 1
        try:
            data = simulation_db.read_json(run_dir.join(template_common.INPUT_BASE_NAME))
            with h5py.File(str(diag_file), 'r') as f:
                size = f['emitx'].shape[0]
                turn = int(f['repetition'][-1]) + 1
                complete = 100 * (turn - 0.5) / data.models.simulationSettings.turn_count
                res = PKDict(
                    percentComplete=complete if is_running else 100,
                    frameCount=size,
                    turnCount=turn,
                )
                res['bunchAnimation.frameCount'] = particle_file_count
                return res

        except Exception:
            # file present but not hdf formatted
            pass
    return PKDict(
        percentComplete=0,
        frameCount=0,
    )


def format_float(v):
    return float(format(v, '.10f'))


def get_application_data(data, **kwargs):
    if data.method == 'calculate_bunch_parameters':
        return _calc_bunch_parameters(data.bunch)
    if data.method == 'compute_particle_ranges':
        return template_common.compute_field_range(data, _compute_range_across_files)
    assert False, 'unknown application data method: {}'.format(data.method)


def import_file(req, tmp_dir=None, **kwargs):
    if re.search(r'.madx$', req.filename, re.IGNORECASE):
        data = _import_madx_file(req.file_stream.read())
    elif re.search(r'.mad8$', req.filename, re.IGNORECASE):
        import pyparsing
        try:
            data = _import_mad8_file(req.file_stream.read())
        except pyparsing.ParseException as e:
            # ParseException has no message attribute
            raise sirepo.util.UserAlert(str(e))
    elif re.search(r'.lte$', req.filename, re.IGNORECASE):
        data = _import_elegant_file(req.file_stream.read())
    else:
        raise sirepo.util.UserAlert('invalid file extension, expecting .madx or .mad8')
    LatticeUtil(data, _SCHEMA).sort_elements_and_beamlines()
    data.models.simulation.name = re.sub(r'\.(mad.|lte)$', '', req.filename, flags=re.IGNORECASE)
    return data


def get_data_file(run_dir, model, frame, options=None, **kwargs):
    if model in OUTPUT_FILE:
        path = run_dir.join(OUTPUT_FILE[model])
    elif model == 'bunchAnimation':
        path = py.path.local(_particle_file_list(run_dir)[frame])
    elif 'bunchReport' in model:
        path = run_dir.join(OUTPUT_FILE.bunchReport)
    else:
        assert False, 'model data file not yet supported: {}'.format(model)
    with open(str(path)) as f:
        return path.basename, f.read(), 'application/octet-stream'


def label(field, enum_labels=None):
    res = field
    if enum_labels:
        for values in enum_labels:
            if field == values[0]:
                res = values[1]
    if field not in _UNITS:
        return res
    return '{} [{}]'.format(res, _UNITS[field])


def post_execution_processing(success_exit=True, is_parallel=False, run_dir=None, **kwargs):
    if success_exit:
        return None
    if not is_parallel:
        return _parse_synergia_log(run_dir)
    e = None
    f = run_dir.join('mpi_run.out')
    if f.exists():
        m = re.search(
            r'^Traceback .*?^\w*Error: (.*?)\n',
            pkio.read_text(f),
            re.MULTILINE | re.DOTALL,
        )
        if m:
            e = m.group(1)
    return e


def prepare_sequential_output_file(run_dir, data):
    report = data.report
    if 'bunchReport' in report or 'twissReport' in report:
        fn = simulation_db.json_filename(template_common.OUTPUT_BASE_NAME, run_dir)
        if fn.exists():
            fn.remove()
            save_sequential_report_data(data, run_dir)


def python_source_for_model(data, model):
    return _generate_parameters_file(data)


def save_sequential_report_data(data, run_dir):
    if 'bunchReport' in data.report:
        import synergia.bunch
        with h5py.File(str(run_dir.join(OUTPUT_FILE.twissReport)), 'r') as f:
            twiss0 = dict(map(
                lambda k: (k, format_float(f[k][0])),
                ('alpha_x', 'alpha_y', 'beta_x', 'beta_y'),
            ))
        report = data.models[data.report]
        bunch = data.models.bunch
        if bunch.distribution == 'file':
            bunch_file = _SIM_DATA.lib_file_name_with_model_field('bunch', 'particleFile', bunch.particleFile)
        else:
            bunch_file = OUTPUT_FILE.bunchReport
        if not run_dir.join(bunch_file).exists():
            return
        with h5py.File(str(run_dir.join(bunch_file)), 'r') as f:
            x = f['particles'][:, getattr(synergia.bunch.Bunch, report['x'])]
            y = f['particles'][:, getattr(synergia.bunch.Bunch, report['y'])]
        res = template_common.heatmap([x, y], report, {
            'title': '',
            'x_label': label(report.x, _SCHEMA.enum.PhaseSpaceCoordinate8),
            'y_label': label(report.y, _SCHEMA.enum.PhaseSpaceCoordinate8),
            'summaryData': {
                'bunchTwiss': twiss0,
            },
        })
    else:
        report_name = data.report
        x = None
        plots = []
        report = data.models[report_name]
        with h5py.File(str(run_dir.join(OUTPUT_FILE[report_name])), 'r') as f:
            x = f['s'][:].tolist()
            for yfield in ('y1', 'y2', 'y3'):
                if report[yfield] == 'none':
                    continue
                name = report[yfield]
                plots.append({
                    'name': name,
                    'label': label(report[yfield], _SCHEMA.enum.TwissParameter),
                    'points': f[name][:].tolist(),
                })
        res = {
            'title': '',
            'x_range': [min(x), max(x)],
            'y_range': template_common.compute_plot_color_and_range(plots),
            'x_label': 's [m]',
            'y_label': '',
            'x_points': x,
            'plots': plots,
        }
    template_common.write_sequential_result(res, run_dir=run_dir)


def sim_frame_beamEvolutionAnimation(frame_args):
    plots = []
    n = str(frame_args.run_dir.join(OUTPUT_FILE.beamEvolutionAnimation))
    with h5py.File(n, 'r') as f:
        x = f['s'][:].tolist()
        for yfield in ('y1', 'y2', 'y3'):
            if frame_args[yfield] == 'none':
                continue
            points = _plot_values(f, frame_args[yfield])
            for v in points:
                if isinstance(v, float) and (math.isinf(v) or math.isnan(v)):
                    return _parse_synergia_log(frame_args.run_dir) or PKDict(
                        error='Invalid data computed',
                    )
            plots.append(PKDict(
                points=points,
                label=label(frame_args[yfield], _SCHEMA.enum.BeamColumn),
            ))
        return PKDict(
            title='',
            x_range=[min(x), max(x)],
            y_label='',
            x_label='s [m]',
            x_points=x,
            plots=plots,
            y_range=template_common.compute_plot_color_and_range(plots),
        )


def sim_frame_bunchAnimation(frame_args):
    n = _particle_file_list(frame_args.run_dir)[frame_args.frameIndex]
    with h5py.File(str(n), 'r') as f:
        x = f['particles'][:, _COORD6.index(frame_args.x)].tolist()
        y = f['particles'][:, _COORD6.index(frame_args.y)].tolist()
        if 'bunchAnimation' not in frame_args.sim_in.models:
            # In case the simulation was run before the bunchAnimation was added
            return PKDict(error='report not generated')
        tlen = f['tlen'][()]
        s_n = f['s_n'][()]
        rep = 0 if s_n == 0 else int(round(tlen / s_n))
        model = frame_args.sim_in.models.bunchAnimation
        model.update(frame_args)
        return template_common.heatmap(
            [x, y],
            model,
            PKDict(
                x_label=label(frame_args.x),
                y_label=label(frame_args.y),
                title='{}-{} at {:.1f}m, turn {}'.format(frame_args.x, frame_args.y, tlen, rep),
            ),
        )


def sim_frame_turnComparisonAnimation(frame_args):
    turn_count = frame_args.sim_in.models.simulationSettings.turn_count
    plots = []
    with h5py.File(str(frame_args.run_dir.join(OUTPUT_FILE.beamEvolutionAnimation)), 'r') as f:
        x = f['s'][:].tolist()
        points = _plot_values(f, frame_args.y)
        for v in points:
            if isinstance(v, float) and (math.isinf(v) or math.isnan(v)):
                return _parse_synergia_log(frame_args.run_dir) or {
                    'error': 'Invalid data computed',
                }
        steps = (len(points) - 1) / turn_count
        x = x[0:int(steps + 1)]
        if not frame_args.turn1 or int(frame_args.turn1) > turn_count:
            frame_args.turn1 = 1
        if not frame_args.turn2 or int(frame_args.turn2) > turn_count or int(frame_args.turn1) == int(frame_args.turn2):
            frame_args.turn2 = turn_count
        for yfield in ('turn1', 'turn2'):
            turn = int(frame_args[yfield])
            p = points[int((turn - 1) * steps):int((turn - 1) * steps + steps + 1)]
            if not len(p):
                return {
                    'error': 'Simulation data is not yet available',
                }
            plots.append({
                'points': p,
                'label': '{} turn {}'.format(label(frame_args.y, _SCHEMA.enum.BeamColumn), turn),
            })
        return {
            'title': '',
            'x_range': [min(x), max(x)],
            'y_label': '',
            'x_label': 's [m]',
            'x_points': x,
            'plots': plots,
            'y_range': template_common.compute_plot_color_and_range(plots),
        }


def validate_file(file_type, path):
    if file_type != 'bunch-particleFile':
        return 'invalid file type'
    try:
        with h5py.File(path, 'r') as f:
            if 'particles' in f:
                shape = f['particles'].shape
                if shape[1] < 7:
                    return 'expecting 7 columns in hdf5 file'
                elif shape[0] == 0:
                    return 'no data rows in hdf5 file'
            else:
                return 'hdf5 file missing particles dataset'
    except IOError as e:
        return 'invalid hdf5 file'
    return None


def write_parameters(data, run_dir, is_parallel):
    pkio.write_text(
        run_dir.join(template_common.PARAMETERS_PYTHON_FILE),
        _generate_parameters_file(data),
    )


def _calc_bunch_parameters(bunch):
    bunch_def = bunch.beam_definition
    bunch_enums = get_enums(_SCHEMA, 'BeamDefinition')
    mom = foundation.Four_momentum(bunch.mass)
    _calc_particle_info(bunch)
    try:
        if bunch_def == bunch_enums.energy:
            mom.set_total_energy(bunch.energy)
        elif bunch_def == bunch_enums.momentum:
            mom.set_momentum(bunch.momentum)
        elif bunch_def == bunch_enums.gamma:
            mom.set_gamma(bunch.gamma)
        else:
            assert False, 'invalid bunch def: {}'.format(bunch_def)
        bunch.gamma = format_float(mom.get_gamma())
        bunch.energy = format_float(mom.get_total_energy())
        bunch.momentum = format_float(mom.get_momentum())
        bunch.beta = format_float(mom.get_beta())
    except Exception as e:
        bunch[bunch_def] = ''
    return {
        'bunch': bunch,
    }


def _calc_particle_info(bunch):
    from synergia.foundation import pconstants
    particle = bunch.particle
    particle_enums = get_enums(_SCHEMA, 'Particle')
    if particle == particle_enums.other:
        return
    mass = 0
    charge = 0
    if particle == particle_enums.proton:
        mass = pconstants.mp
        charge = pconstants.proton_charge
    # No antiprotons yet - commented out to avoid assertion error
    #elif particle == particle_enums.antiproton:
    #    mass = pconstants.mp
    #    charge = pconstants.antiproton_charge
    elif particle == particle_enums.electron:
        mass = pconstants.me
        charge = pconstants.electron_charge
    elif particle == particle_enums.positron:
        mass = pconstants.me
        charge = pconstants.positron_charge
    elif particle == particle_enums.negmuon:
        mass = pconstants.mmu
        charge = pconstants.muon_charge
    elif particle == particle_enums.posmuon:
        mass = pconstants.mmu
        charge = pconstants.antimuon_charge
    else:
        assert False, 'unknown particle: {}'.format(particle)
    bunch.mass = mass
    bunch.charge = charge


def _compute_range_across_files(run_dir, data):
    res = PKDict()
    for v in _SCHEMA.enum.PhaseSpaceCoordinate6:
        res[v[0]] = []
    for filename in _particle_file_list(run_dir):
        with h5py.File(str(filename), 'r') as f:
            for field in res:
                values = f['particles'][:, _COORD6.index(field)].tolist()
                if len(res[field]):
                    res[field][0] = min(min(values), res[field][0])
                    res[field][1] = max(max(values), res[field][1])
                else:
                    res[field] = [min(values), max(values)]
    return res


def _drift_name(length):
    return 'D{}'.format(length).replace('.', '_')


def _format_field_value(state, model, field, el_type):
    value = model[field];
    if el_type in _QUOTED_MADX_FIELD:
        value = '"{}"'.format(value)
    return [field, value]


def _generate_lattice(data, util):
    return util.render_lattice_and_beamline(SynergiaLatticeIterator(_format_field_value), want_semicolon=True)


def _generate_parameters_file(data):
    _validate_data(data, _SCHEMA)
    res, v = template_common.generate_parameters_file(data)
    util = LatticeUtil(data, _SCHEMA)
    v.update({
        'lattice': _generate_lattice(data, util),
        'use_beamline': util.select_beamline().name.lower(),
        'bunchFileName': OUTPUT_FILE.bunchReport,
        'diagnosticFilename': OUTPUT_FILE.beamEvolutionAnimation,
        'twissFileName': OUTPUT_FILE.twissReport,
    })
    if data.models.bunch.distribution == 'file':
        v.bunchFile = _SIM_DATA.lib_file_name_with_model_field('bunch', 'particleFile', data.models.bunch.particleFile)
    v.bunch = template_common.render_jinja(SIM_TYPE, v, 'bunch.py')
    res += template_common.render_jinja(SIM_TYPE, v, 'base.py')
    report = data.report if 'report' in data else ''
    if 'bunchReport' in report or 'twissReport' in report:
        res += template_common.render_jinja(SIM_TYPE, v, 'twiss.py')
        if 'bunchReport' in report:
            res += template_common.render_jinja(SIM_TYPE, v, 'bunch-report.py')
    else:
        res += template_common.render_jinja(SIM_TYPE, v, 'parameters.py')
    return res


def _import_bunch(lattice, data):
    from synergia.foundation import pconstants
    if not lattice.has_reference_particle():
        # create a default reference particle, proton,energy=1.5
        lattice.set_reference_particle(
            foundation.Reference_particle(
                pconstants.proton_charge,
                foundation.Four_momentum(pconstants.mp, 1.5)
            )
        )
    ref = lattice.get_reference_particle()
    four_momentum = ref.get_four_momentum()
    bunch = data.models.bunch
    bunch.update({
        'beam_definition': 'gamma',
        'charge': ref.get_charge(),
        'gamma': format_float(four_momentum.get_gamma()),
        'energy': format_float(four_momentum.get_total_energy()),
        'momentum': format_float(four_momentum.get_momentum()),
        'beta': format_float(four_momentum.get_beta()),
        'mass': format_float(four_momentum.get_mass()),
        'particle': 'other',
    })
    if bunch.mass == pconstants.mp:
        if bunch.charge == pconstants.proton_charge:
            bunch.particle = 'proton'
        #TODO(pjm): antiproton (anti-proton) not working with synergia
    elif bunch.mass == pconstants.me:
        bunch.particle = 'positron' if bunch.charge == pconstants.positron_charge else 'electron'
    elif bunch.mass == pconstants.mmu:
        bunch.particle = 'posmuon' if bunch.charge == pconstants.antimuon_charge else 'negmuon'

_ELEGANT_NAME_MAP = PKDict(
    DRIF='DRIFT',
    CSRDRIFT='DRIFT',
    SBEN='SBEND',
    KSBEND='SBEND',
    CSBEND='SBEND',
    CSRCSBEND='SBEND',
    QUAD='QUADRUPOLE',
    KQUAD='QUADRUPOLE',
    SEXT='SEXTUPOLE',
    KSEXT='SEXTUPOLE',
    MARK='MARKER',
    HCOR='HKICKER',
    HVCOR='HKICKER',
    EHCOR='HKICKER',
    VCOR='VKICKER',
    EVCOR='VKICKER',
    EHVCOR='KICKER',
    RFCA='RFCAVITY',
    HKICK='HKICKER',
    VKICK='VKICKER',
    KICK='KICKER',
    SOLE='SOLENOID',
    HMON='HMONITOR',
    VMON='VMONITOR',
    MONI='MONITOR',
    ECOL='ECOLLIMATOR',
    RCOL='RCOLLIMATOR',
    ROTATE='SROTATION',
)

_ELEGANT_FIELD_MAP = PKDict(
    ECOL=PKDict(
        x_max='xsize',
        y_max='ysize',
    ),
    RCOL=PKDict(
        x_max='xsize',
        y_max='ysize',
    ),
    ROTATE=PKDict(
        tilt='angle',
    )
)

def _import_elegant_file(text):
    try:
        from sirepo.template import elegant_lattice_importer
    except AssertionError:
        assert False, 'The elegant sirepo application is not configured.'
    elegant_data = elegant_lattice_importer.import_file(text)
    rpn_cache = elegant_data.models.rpnCache
    data = simulation_db.default_data(SIM_TYPE)
    element_ids = {}
    for el in elegant_data.models.elements:
        if el.type not in _ELEGANT_NAME_MAP:
            if 'l' in el:
                el.name += '_{}'.format(el.type)
                el.type = 'DRIF'
            else:
                continue
        el.name = re.sub(r':', '_', el.name)
        name = _ELEGANT_NAME_MAP[el.type]
        schema = _SCHEMA.model[name]
        m = PKDict(
            _id=el._id,
            type=name,
        )
        for f in el:
            v = el[f]
            if el.type in _ELEGANT_FIELD_MAP and f in _ELEGANT_FIELD_MAP[el.type]:
                f = _ELEGANT_FIELD_MAP[el.type][f]
            if f in schema:
                if v in rpn_cache:
                    v = rpn_cache[v]
                m[f] = v
        _SIM_DATA.update_model_defaults(m, name)
        data.models.elements.append(m)
        element_ids[m._id] = True
    beamline_ids = {}
    for bl in elegant_data.models.beamlines:
        bl.name = re.sub(r':', '_', bl.name)
        element_ids[bl.id] = True
        element_ids[-bl.id] = True
    for bl in elegant_data.models.beamlines:
        items = []
        for element_id in bl['items']:
            if element_id in element_ids:
                items.append(element_id)
        data.models.beamlines.append(PKDict(
            id=bl.id,
            items=items,
            name=bl.name,
        ))
    elegant_sim = elegant_data.models.simulation
    if 'activeBeamlineId' in elegant_sim:
        data.models.simulation.activeBeamlineId = elegant_sim.activeBeamlineId
        data.models.simulation.visualizationBeamlineId = elegant_sim.activeBeamlineId
    return data


def _import_elements(lattice, data):
    name_to_id = {}
    beamline = data.models.beamlines[0]
    current_id = beamline.id

    for el in lattice.get_elements():
        attrs = {}
        for attr in el.get_double_attributes():
            attrs[attr] = el.get_double_attribute(attr)
        for attr in el.get_string_attributes():
            attrs[attr] = el.get_string_attribute(attr)
        for attr in el.get_vector_attributes():
            attrs[attr] = '{' + ','.join(map(str, el.get_vector_attribute(attr))) + '}'
        model_name = el.get_type().upper()
        if model_name not in _SCHEMA.model:
            raise IOError('Unsupported element type: {}'.format(model_name))
        m = _SIM_DATA.model_defaults(model_name)
        if 'l' in attrs:
            attrs['l'] = float(str(attrs['l']))
        if model_name == 'DRIFT' and re.search(r'^auto_drift', el.get_name()):
            drift_name = _drift_name(attrs['l'])
            m.name = drift_name
        else:
            m.name = el.get_name().upper()
        if m.name in name_to_id:
            beamline['items'].append(name_to_id[m.name])
            continue
        m.type = model_name
        current_id += 1
        beamline['items'].append(current_id)
        m._id = current_id
        name_to_id[m.name] = m._id
        info = _SCHEMA.model[model_name]
        for f in info.keys():
            if f in attrs:
                m[f] = attrs[f]
        for attr in attrs:
            if attr not in m:
                if attr not in _IGNORE_ATTRIBUTES:
                    pkdlog('unknown attr: {}: {}'.format(model_name, attr))
        data.models.elements.append(m)


def _import_mad_file(reader, beamline_names):
    data = simulation_db.default_data(SIM_TYPE)
    lattice = _import_main_beamline(reader, data, beamline_names)
    _import_elements(lattice, data)
    _import_bunch(lattice, data)
    return data


def _import_mad8_file(text):
    import synergia
    reader = synergia.lattice.Mad8_reader()
    reader.parse_string(text)
    return _import_mad_file(reader, reader.get_lines())


def _import_madx_file(text):
    import synergia
    reader = synergia.lattice.MadX_reader()
    reader.parse(text)
    return _import_mad_file(reader, reader.get_line_names() + reader.get_sequence_names())


def _import_main_beamline(reader, data, beamline_names):
    lines = {}
    for name in beamline_names:
        names = []
        for el in reader.get_lattice(name).get_elements():
            names.append(el.get_name())
        lines[name] = names
    #TODO(pjm): assumes longest sequence is it target beamline
    beamline_name = _sort_beamlines_by_length(lines)[0][0]
    res = reader.get_lattice(beamline_name)
    current_id = 1
    data.models.beamlines.append(PKDict(
        id=current_id,
        items=[],
        name=beamline_name,
    ))
    data.models.simulation.activeBeamlineId = current_id
    data.models.simulation.visualizationBeamlineId = current_id
    return res


def _nlinsert_drift(model, size):
    return PKDict(
        name=_nlinsert_name(model, _drift_name(size)),
        type='DRIFT',
        l=size,
        _id=0,
    )


def _nlinsert_field_values(model, id_map):
    # explode and iterate the NLINSERT element
    import rsbeams.rslattice.nonlinear
    nli = rsbeams.rslattice.nonlinear.NonlinearInsert(
        float(model.l),
        float(model.phase),
        float(model.t),
        float(model.c),
        int(model.num_slices)
    )
    nli.generate_sequence()
    d1 = _nlinsert_drift(model, nli.s_vals[0])
    d2 = _nlinsert_drift(model, nli.s_vals[0] * 2)
    elements = [d1, d2]
    names = [d1.name]
    for idx in range(len(nli.knll)):
        name = _nlinsert_name(model, str(idx + 1))
        elements.append(PKDict(
            name=name,
            type='NLLENS',
            extractor_type=model.extractor_type,
            knll=nli.knll[idx],
            cnll=nli.cnll[idx],
            _id=0,
        ))
        names.append(name)
        names.append(d2.name)
    names = names[:-1]
    names.append(d1.name)
    id_map[model._id].name = ','.join(names)
    return LatticeUtil(
        PKDict(
            models=PKDict(
                elements=elements,
                beamlines=[],
            ),
        ),
        _SCHEMA,
    ).iterate_models(
        SynergiaLatticeIterator(_format_field_value),
        'elements',
    ).result


def _nlinsert_name(model, el_name):
    return '{}.NLINSERT.{}'.format(model.name, el_name).upper()


def _parse_synergia_log(run_dir):
    if not run_dir.join(template_common.RUN_LOG).exists():
        return None
    text = pkio.read_text(run_dir.join(template_common.RUN_LOG))
    errors = []
    current = ''
    for line in text.split("\n"):
        if not line:
            if current:
                errors.append(current)
                current = ''
            continue
        m = re.match('\*\*\* (WARR?NING|ERROR) \*\*\*(.*)', line)
        if m:
            if not current:
                error_type = m.group(1)
                if error_type == 'WARRNING':
                    error_type = 'WARNING'
                current = '{}: '.format(error_type)
            extra = m.group(2)
            if re.search(r'\S', extra) and not re.search(r'File:|Line:|line \d+', extra):
                current += '\n' + extra
        elif current:
            current += '\n' + line
        else:
            m = re.match('Propagator:*(.*?)Exiting', line)
            if m:
                errors.append(m.group(1))
    if len(errors):
        return '\n\n'.join(errors)
    return None


def _particle_file_list(run_dir):
    return sorted(glob.glob(str(run_dir.join('particles_*.h5'))))


def _plot_field(field):
    if field == 'numparticles':
        return 'num_particles', None, None
    m = re.match('(\w+)emit', field)
    if m:
        return 'emit{}'.format(m.group(1)), m.group(1), None
    m = re.match('(\w+)(mean|std)', field)
    if m:
        return m.group(2), m.group(1), None
    m = re.match('^(\wp?)(\wp?)(corr|mom2)', field)
    if m:
        return m.group(3), m.group(1), m.group(2)
    assert False, 'unknown field: {}'.format(field)


def _plot_values(h5file, field):
    name, coord1, coord2 = _plot_field(field)
    dimension = len(h5file[name].shape)
    if dimension == 1:
        return h5file[name][:].tolist()
    if dimension == 2:
        return h5file[name][_COORD6.index(coord1), :].tolist()
    if dimension == 3:
        return h5file[name][_COORD6.index(coord1), _COORD6.index(coord2), :].tolist()
    assert False, dimension


def _sort_beamlines_by_length(lines):
    res = []
    for name in lines:
        res.append([name, len(lines[name])])
    return list(reversed(sorted(res, key=lambda v: v[1])))


def _validate_data(data, schema):
    # ensure enums match, convert ints/floats, apply scaling
    enum_info = template_common.validate_models(data, schema)
    for m in data.models.elements:
        template_common.validate_model(
            m,
            schema.model[LatticeUtil.model_name_for_data(m)],
            enum_info)
