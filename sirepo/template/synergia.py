# -*- coding: utf-8 -*-
u"""Synergia execution template.

:copyright: Copyright (c) 2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from __future__ import absolute_import, division, print_function
from pykern import pkio
from pykern.pkdebug import pkdc, pkdp, pkdlog
from sirepo import simulation_db
from sirepo.srschema import get_enums
from sirepo.template import template_common, elegant_common, elegant_lattice_importer
from synergia import foundation
import glob
import h5py
import math
import py.path
import re
import werkzeug

OUTPUT_FILE = {
    'bunchReport': 'particles.h5',
    'twissReport': 'twiss.h5',
    'twissReport2': 'twiss.h5',
    'beamEvolutionAnimation': 'diagnostics.h5',
    'turnComparisonAnimation': 'diagnostics.h5',
}

SIM_TYPE = 'synergia'

WANT_BROWSER_FRAME_CACHE = True

_COORD6 = ['x', 'xp', 'y', 'yp', 'z', 'zp']

_FILE_ID_SEP = '-'

_IGNORE_ATTRIBUTES = ['lrad']

_SCHEMA = simulation_db.get_schema(SIM_TYPE)

_UNITS = {
    'x': 'm',
    'y': 'm',
    'z': 'm',
    'xp': 'rad',
    'yp': 'rad',
    'zp': 'rad',
    'cdt': 'm',
    'xstd': 'm',
    'ystd': 'm',
    'zstd': 'm',
    'xmean': 'm',
    'ymean': 'm',
    'zmean': 'm',
    'beta_x': 'm',
    'beta_y': 'm',
    'psi_x': 'rad',
    'psi_y': 'rad',
    'D_x': 'm',
    'D_y': 'm',
    'Dprime_x': 'rad',
    'Dprime_y': 'rad',
}


def background_percent_complete(report, run_dir, is_running):
    diag_file = run_dir.join(OUTPUT_FILE['beamEvolutionAnimation'])
    if diag_file.exists():
        particle_file_count = len(_particle_file_list(run_dir))
        # if is_running:
        #     particle_file_count -= 1
        try:
            data = simulation_db.read_json(run_dir.join(template_common.INPUT_BASE_NAME))
            with h5py.File(str(diag_file), 'r') as f:
                size = f['emitx'].shape[0]
                turn = int(f['repetition'][-1]) + 1
                complete = 100 * (turn - 0.5) / data['models']['simulationSettings']['turn_count']
                return {
                    'percentComplete': complete if is_running else 100,
                    'frameCount': size,
                    'turnCount': turn,
                    'bunchAnimation.frameCount': particle_file_count,
                }
        except Exception as e:
            # file present but not hdf formatted
            pass
    return {
        'percentComplete': 0,
        'frameCount': 0,
    }


def fixup_old_data(data):
    for m in [
            'beamEvolutionAnimation',
            'bunch',
            'bunchAnimation',
            'bunchTwiss',
            'simulationSettings',
            'turnComparisonAnimation',
            'twissReport',
            'twissReport2',
    ]:
        if m not in data['models']:
            data['models'][m] = {}
        template_common.update_model_defaults(data['models'][m], m, _SCHEMA)
    if 'bunchReport' in data['models']:
        del data['models']['bunchReport']
        for i in range(4):
            m = 'bunchReport{}'.format(i + 1)
            model = data['models'][m] = {}
            template_common.update_model_defaults(data['models'][m], 'bunchReport', _SCHEMA)
            if i == 0:
                model['y'] = 'xp'
            elif i == 1:
                model['x'] = 'y'
                model['y'] = 'yp'
            elif i == 3:
                model['x'] = 'z'
                model['y'] = 'zp'
    template_common.organize_example(data)


def format_float(v):
    return float(format(v, '.10f'))


def get_animation_name(data):
    return 'animation'


def get_application_data(data):
    if data['method'] == 'calculate_bunch_parameters':
        return _calc_bunch_parameters(data['bunch'])
    if data['method'] == 'compute_particle_ranges':
        return template_common.compute_field_range(data, _compute_range_across_files)
    assert False, 'unknown application data method: {}'.format(data['method'])


def import_file(request, lib_dir=None, tmp_dir=None):
    f = request.files['file']
    filename = werkzeug.secure_filename(f.filename)
    if re.search(r'.madx$', filename, re.IGNORECASE):
        data = _import_madx_file(f.read())
    elif re.search(r'.mad8$', filename, re.IGNORECASE):
        import pyparsing
        try:
            data = _import_mad8_file(f.read())
        except pyparsing.ParseException as e:
            # ParseException has no message attribute
            raise IOError(str(e))
    elif re.search(r'.lte$', filename, re.IGNORECASE):
        data = _import_elegant_file(f.read())
    else:
        raise IOError('invalid file extension, expecting .madx or .mad8')
    elegant_common.sort_elements_and_beamlines(data)
    data['models']['simulation']['name'] = re.sub(r'\.(mad.|lte)$', '', filename, flags=re.IGNORECASE)
    return data


def get_data_file(run_dir, model, frame, options=None):
    if model in OUTPUT_FILE:
        path = run_dir.join(OUTPUT_FILE[model])
    elif model == 'bunchAnimation':
        path = py.path.local(_particle_file_list(run_dir)[frame])
    elif model == 'beamlineReport':
        data = simulation_db.read_json(str(run_dir.join('..', simulation_db.SIMULATION_DATA_FILE)))
        source = _generate_parameters_file(data)
        return 'python-source.py', source, 'text/plain'
    else:
        assert False, 'model data file not yet supported: {}'.format(model)
    with open(str(path)) as f:
        return path.basename, f.read(), 'application/octet-stream'


def get_simulation_frame(run_dir, data, model_data):
    frame_index = int(data['frameIndex'])
    if data['modelName'] == 'beamEvolutionAnimation':
        args = template_common.parse_animation_args(
            data,
            {
                '1': ['x', 'y1', 'y2', 'y3', 'startTime'],
                '': ['y1', 'y2', 'y3', 'startTime'],
            },
        )
        return _extract_evolution_plot(args, run_dir)
    if data['modelName'] == 'bunchAnimation':
        args = template_common.parse_animation_args(
            data,
            {
                '1': ['x', 'y', 'histogramBins', 'startTime'],
                '': ['x', 'y', 'histogramBins', 'plotRangeType', 'horizontalSize', 'horizontalOffset', 'verticalSize', 'verticalOffset', 'isRunning', 'startTime'],
            },
        )
        return _extract_bunch_plot(args, frame_index, run_dir)
    if data['modelName'] == 'turnComparisonAnimation':
        args = template_common.parse_animation_args(
            data,
            {
                '': ['y', 'turn1', 'turn2', 'startTime'],
            },
        )
        return _extract_turn_comparison_plot(args, run_dir, model_data.models.simulationSettings.turn_count)
    raise RuntimeError('unknown animation model: {}'.format(data['modelName']))


def label(field, enum_labels=None):
    res = field
    if enum_labels:
        for values in enum_labels:
            if field == values[0]:
                res = values[1]
    if field not in _UNITS:
        return res
    return '{} [{}]'.format(res, _UNITS[field])


def lib_files(data, source_lib):
    return template_common.filename_to_path(_simulation_files(data), source_lib)


def models_related_to_report(data):
    r = data['report']
    if r == 'animation':
        return []
    res = ['beamlines', 'elements']
    if 'bunchReport' in r:
        res += ['bunch', 'simulation.visualizationBeamlineId']
    elif 'twissReport' in r:
        res += ['simulation.{}'.format(_beamline_id_for_report(r))]
    return res


def parse_error_log(run_dir):
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
        return {'state': 'error', 'error': '\n\n'.join(errors)}
    return None


def python_source_for_model(data, model):
    return _generate_parameters_file(data)


def prepare_output_file(run_dir, data):
    report = data['report']
    if 'bunchReport' in report or 'twissReport' in report:
        fn = simulation_db.json_filename(template_common.OUTPUT_BASE_NAME, run_dir)
        if fn.exists():
            fn.remove()
            save_report_data(data, run_dir)


def remove_last_frame(run_dir):
    pass


def save_report_data(data, run_dir):
    if 'bunchReport' in data['report']:
        import synergia.bunch
        with h5py.File(str(run_dir.join(OUTPUT_FILE['twissReport'])), 'r') as f:
            twiss0 = dict(map(
                lambda k: (k, format_float(f[k][0])),
                ('alpha_x', 'alpha_y', 'beta_x', 'beta_y'),
            ))
        report = data.models[data['report']]
        bunch = data.models.bunch
        if bunch.distribution == 'file':
            bunch_file = template_common.lib_file_name('bunch', 'particleFile', bunch.particleFile)
        else:
            bunch_file = OUTPUT_FILE['bunchReport']
        if not run_dir.join(bunch_file).exists():
            return
        with h5py.File(str(run_dir.join(bunch_file)), 'r') as f:
            x = f['particles'][:, getattr(synergia.bunch.Bunch, report['x'])]
            y = f['particles'][:, getattr(synergia.bunch.Bunch, report['y'])]
        res = template_common.heatmap([x, y], report, {
            'title': '',
            'x_label': label(report['x'], _SCHEMA['enum']['PhaseSpaceCoordinate8']),
            'y_label': label(report['y'], _SCHEMA['enum']['PhaseSpaceCoordinate8']),
            'summaryData': {
                'bunchTwiss': twiss0,
            },
        })
    else:
        report_name = data['report']
        x = None
        plots = []
        report = data['models'][report_name]
        with h5py.File(str(run_dir.join(OUTPUT_FILE[report_name])), 'r') as f:
            x = f['s'][:].tolist()
            for yfield in ('y1', 'y2', 'y3'):
                if report[yfield] == 'none':
                    continue
                name = report[yfield]
                plots.append({
                    'name': name,
                    'label': label(report[yfield], _SCHEMA['enum']['TwissParameter']),
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
    simulation_db.write_result(res, run_dir=run_dir)


def simulation_dir_name(report_name):
    if 'bunchReport' in report_name:
        return 'bunchReport'
    return report_name


def validate_file(file_type, path):
    assert file_type == 'bunch-particleFile'
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


#TODO(pjm): from template.elegant
def _add_beamlines(beamline, beamlines, ordered_beamlines):
    if beamline in ordered_beamlines:
        return
    for id in beamline['items']:
        id = abs(id)
        if id in beamlines:
            _add_beamlines(beamlines[id], beamlines, ordered_beamlines)
    ordered_beamlines.append(beamline)


def _append_to_lattice(state, madx_text):
    if state['lattice']:
        state['lattice'] = state['lattice'][:-1]
        state['lattice'] += ';\n'
    state['lattice'] += madx_text


def _beamline_id_for_report(r):
    return 'activeBeamlineId' if r == 'twissReport' else 'visualizationBeamlineId'


#TODO(pjm): from template.elegant
def _build_beamline_map(data):
    res = {}
    for bl in data['models']['beamlines']:
        res[bl['id']] = bl['name']
    return res


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
    res = {}
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


def _extract_bunch_plot(report, frame_index, run_dir):
    filename = _particle_file_list(run_dir)[frame_index]
    with h5py.File(str(filename), 'r') as f:
        x = f['particles'][:, _COORD6.index(report['x'])].tolist()
        y = f['particles'][:, _COORD6.index(report['y'])].tolist()
        data = simulation_db.read_json(run_dir.join(template_common.INPUT_BASE_NAME))
        if 'bunchAnimation' not in data.models:
            # In case the simulation was run before the bunchAnimation was added
            return {
                'error': 'Report not generated',
            }
        tlen = f['tlen'][()]
        s_n = f['s_n'][()]
        rep = 0 if s_n == 0 else int(round(tlen / s_n))
        model = data.models.bunchAnimation
        model.update(report)
        return template_common.heatmap([x, y], model, {
            'x_label': label(report['x']),
            'y_label': label(report['y']),
            'title': '{}-{} at {:.1f}m, turn {}'.format(report['x'], report['y'], tlen, rep),
        })


def _extract_evolution_plot(report, run_dir):
    plots = []
    with h5py.File(str(run_dir.join(OUTPUT_FILE['beamEvolutionAnimation'])), 'r') as f:
        x = f['s'][:].tolist()
        for yfield in ('y1', 'y2', 'y3'):
            if report[yfield] == 'none':
                continue
            points = _plot_values(f, report[yfield])
            for v in points:
                if isinstance(v, float) and (math.isinf(v) or math.isnan(v)):
                    return parse_error_log(run_dir) or {
                        'error': 'Invalid data computed',
                    }
            plots.append({
                'points': points,
                'label': label(report[yfield], _SCHEMA['enum']['BeamColumn']),
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


def _extract_turn_comparison_plot(report, run_dir, turn_count):
    plots = []
    with h5py.File(str(run_dir.join(OUTPUT_FILE['beamEvolutionAnimation'])), 'r') as f:
        x = f['s'][:].tolist()
        points = _plot_values(f, report['y'])
        for v in points:
            if isinstance(v, float) and (math.isinf(v) or math.isnan(v)):
                return parse_error_log(run_dir) or {
                    'error': 'Invalid data computed',
                }
        steps = (len(points) - 1) / turn_count
        x = x[0:int(steps + 1)]
        if not report['turn1'] or int(report['turn1']) > turn_count:
            report['turn1'] = 1
        if not report['turn2'] or int(report['turn2']) > turn_count or int(report['turn1']) == int(report['turn2']):
            report['turn2'] = turn_count
        for yfield in ('turn1', 'turn2'):
            turn = int(report[yfield])
            p = points[int((turn - 1) * steps):int((turn - 1) * steps + steps + 1)]
            if not len(p):
                return {
                    'error': 'Simulation data is not yet available',
                }
            plots.append({
                'points': p,
                'label': '{} turn {}'.format(label(report['y'], _SCHEMA['enum']['BeamColumn']), turn),
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


def _generate_lattice(data, beamline_map, v):
    beamlines = {}
    report = data['report'] if 'report' in data else ''
    beamline_id_field = _beamline_id_for_report(report)

    selected_beamline_id = 0
    sim = data['models']['simulation']
    if beamline_id_field in sim and sim[beamline_id_field]:
        selected_beamline_id = int(sim[beamline_id_field])
    elif len(data['models']['beamlines']):
        selected_beamline_id = data['models']['beamlines'][0]['id']

    for bl in data['models']['beamlines']:
        if selected_beamline_id == int(bl['id']):
            v['use_beamline'] = bl['name'].lower()
        beamlines[bl['id']] = bl

    ordered_beamlines = []

    for id in beamlines:
        _add_beamlines(beamlines[id], beamlines, ordered_beamlines)
    state = {
        'lattice': '',
        'beamline_map': beamline_map,
    }
    _iterate_model_fields(data, state, _iterator_lattice_elements)
    res = state['lattice']
    res = res[:-1]
    res += ';\n'

    for bl in ordered_beamlines:
        if len(bl['items']):
            res += '{}: LINE=('.format(bl['name'].upper())
            for id in bl['items']:
                sign = ''
                if id < 0:
                    sign = '-'
                    id = abs(id)
                res += '{},'.format(sign + beamline_map[id].upper())
            res = res[:-1]
            res += ');\n'
    return res


def _generate_nlinsert_elements(model, state, callback):
    import rsbeams.rslattice.nonlinear
    nli = rsbeams.rslattice.nonlinear.NonlinearInsert(
        float(model['l']),
        float(model['phase']),
        float(model['t']),
        float(model['c']),
        int(model['num_slices'])
    )
    nli.generate_sequence()
    half_size = nli.s_vals[0]
    step_size = half_size * 2
    d1 = _nlinsert_name(model, _drift_name(half_size))
    d2 = _nlinsert_name(model, _drift_name(step_size))
    _append_to_lattice(state, '{}: DRIFT, l={};\n{}: DRIFT, l={};\n'.format(d1, half_size, d2, step_size))
    names = [d1]
    lenses = nli.create_madx()
    extractor = model['extractor_type']
    if extractor == 'default':
        extractor = ''
    else:
        extractor = ', extractor_type="{}"'.format(model['extractor_type'])
    for i in range(len(lenses)):
        name = _nlinsert_name(model, str(i + 1))
        _append_to_lattice(state, '{}: {}{}\n'.format(name, lenses[i][:-1], extractor))
        names.append(name)
        names.append(d2)
    names = names[:-1]
    names.append(d1)
    state['beamline_map'][model['_id']] = ','.join(names)


def _generate_parameters_file(data):
    _validate_data(data, _SCHEMA)
    res, v = template_common.generate_parameters_file(data)
    beamline_map = _build_beamline_map(data)
    v['lattice'] = _generate_lattice(data, beamline_map, v)
    v['bunchFileName'] = OUTPUT_FILE['bunchReport']
    v['diagnosticFilename'] = OUTPUT_FILE['beamEvolutionAnimation']
    v['twissFileName'] = OUTPUT_FILE['twissReport']
    if data.models.bunch.distribution == 'file':
        v['bunchFile'] = template_common.lib_file_name('bunch', 'particleFile', data.models.bunch.particleFile)
    v['bunch'] = template_common.render_jinja(SIM_TYPE, v, 'bunch.py')
    res += template_common.render_jinja(SIM_TYPE, v, 'base.py')
    report = data['report'] if 'report' in data else ''
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
    bunch = data['models']['bunch']
    bunch['beam_definition'] = 'gamma'
    bunch['charge'] = ref.get_charge()
    four_momentum = ref.get_four_momentum()
    bunch['gamma'] = format_float(four_momentum.get_gamma())
    bunch['energy'] = format_float(four_momentum.get_total_energy())
    bunch['momentum'] = format_float(four_momentum.get_momentum())
    bunch['beta'] = format_float(four_momentum.get_beta())
    bunch['mass'] = format_float(four_momentum.get_mass())
    bunch['particle'] = 'other'
    if bunch['mass'] == pconstants.mp:
        if bunch['charge'] == pconstants.proton_charge:
            bunch['particle'] = 'proton'
        #TODO(pjm): antiproton (anti-proton) not working with synergia
    elif bunch['mass'] == pconstants.me:
        bunch['particle'] = 'positron' if bunch['charge'] == pconstants.positron_charge else 'electron'
    elif bunch['mass'] == pconstants.mmu:
        bunch['particle'] = 'posmuon' if bunch['charge'] == pconstants.antimuon_charge else 'negmuon'

_ELEGANT_NAME_MAP = {
    'DRIF': 'DRIFT',
    'CSRDRIFT': 'DRIFT',
    'SBEN': 'SBEND',
    'KSBEND': 'SBEND',
    'CSBEND': 'SBEND',
    'CSRCSBEND': 'SBEND',
    'QUAD': 'QUADRUPOLE',
    'KQUAD': 'QUADRUPOLE',
    'SEXT': 'SEXTUPOLE',
    'KSEXT': 'SEXTUPOLE',
    'MARK': 'MARKER',
    'HCOR': 'HKICKER',
    'HVCOR': 'HKICKER',
    'EHCOR': 'HKICKER',
    'VCOR': 'VKICKER',
    'EVCOR': 'VKICKER',
    'EHVCOR': 'KICKER',
    'RFCA': 'RFCAVITY',
    'HKICK': 'HKICKER',
    'VKICK': 'VKICKER',
    'KICK': 'KICKER',
    'SOLE': 'SOLENOID',
    'HMON': 'HMONITOR',
    'VMON': 'VMONITOR',
    'MONI': 'MONITOR',
    'ECOL': 'ECOLLIMATOR',
    'RCOL': 'RCOLLIMATOR',
    'ROTATE': 'SROTATION',
}

_ELEGANT_FIELD_MAP = {
    'ECOL': {
        'x_max': 'xsize',
        'y_max': 'ysize',
    },
    'RCOL': {
        'x_max': 'xsize',
        'y_max': 'ysize',
    },
    'ROTATE': {
        'tilt': 'angle',
    },
}

def _import_elegant_file(text):
    elegant_data = elegant_lattice_importer.import_file(text)
    rpn_cache = elegant_data['models']['rpnCache']
    data = simulation_db.default_data(SIM_TYPE)
    element_ids = {}
    for el in elegant_data['models']['elements']:
        if el['type'] not in _ELEGANT_NAME_MAP:
            if 'l' in el:
                el['name'] += '_{}'.format(el['type'])
                el['type'] = 'DRIF'
            else:
                continue
        el['name'] = re.sub(r':', '_', el['name'])
        name = _ELEGANT_NAME_MAP[el['type']]
        schema = _SCHEMA['model'][name]
        m = {
            '_id': el['_id'],
            'type': name,
        }
        for f in el:
            v = el[f]
            if el['type'] in _ELEGANT_FIELD_MAP and f in _ELEGANT_FIELD_MAP[el['type']]:
                f = _ELEGANT_FIELD_MAP[el['type']][f]
            if f in schema:
                if v in rpn_cache:
                    v = rpn_cache[v]
                m[f] = v
        template_common.update_model_defaults(m, name, _SCHEMA)
        data['models']['elements'].append(m)
        element_ids[m['_id']] = True
    beamline_ids = {}
    for bl in elegant_data['models']['beamlines']:
        bl['name'] = re.sub(r':', '_', bl['name'])
        element_ids[bl['id']] = True
        element_ids[-bl['id']] = True
    for bl in elegant_data['models']['beamlines']:
        items = []
        for element_id in bl['items']:
            if element_id in element_ids:
                items.append(element_id)
        data['models']['beamlines'].append({
            'id': bl['id'],
            'items': items,
            'name': bl['name'],
        })
    elegant_sim = elegant_data['models']['simulation']
    if 'activeBeamlineId' in elegant_sim:
        data['models']['simulation']['activeBeamlineId'] = elegant_sim['activeBeamlineId']
        data['models']['simulation']['visualizationBeamlineId'] = elegant_sim['activeBeamlineId']
    return data


def _import_elements(lattice, data):
    name_to_id = {}
    beamline = data['models']['beamlines'][0]
    current_id = beamline['id']

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
        m = template_common.model_defaults(model_name, _SCHEMA)
        if 'l' in attrs:
            attrs['l'] = float(str(attrs['l']))
        if model_name == 'DRIFT' and re.search(r'^auto_drift', el.get_name()):
            drift_name = _drift_name(attrs['l'])
            m['name'] = drift_name
        else:
            m['name'] = el.get_name().upper()
        if m['name'] in name_to_id:
            beamline['items'].append(name_to_id[m['name']])
            continue
        m['type'] = model_name
        current_id += 1
        beamline['items'].append(current_id)
        m['_id'] = current_id
        name_to_id[m['name']] = m['_id']
        info = _SCHEMA['model'][model_name]
        for f in info.keys():
            if f in attrs:
                m[f] = attrs[f]
        for attr in attrs:
            if attr not in m:
                if attr not in _IGNORE_ATTRIBUTES:
                    pkdlog('unknown attr: {}: {}'.format(model_name, attr))
        data['models']['elements'].append(m)


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
    data['models']['beamlines'].append({
        'id': current_id,
        'items': [],
        'name': beamline_name,
    })
    data['models']['simulation']['activeBeamlineId'] = current_id
    data['models']['simulation']['visualizationBeamlineId'] = current_id
    return res


#TODO(pjm): from template.elegant
def _iterate_model_fields(data, state, callback):
    for model_type in ['commands', 'elements']:
        #TODO(pjm): no commands in synergia yet
        if model_type == 'commands':
            continue
        for m in data['models'][model_type]:
            model_name = _model_name_for_data(m)
            model_schema = _SCHEMA['model'][model_name]
            callback(state, m)

            for k in sorted(m):
                if k not in model_schema:
                    continue
                element_schema = model_schema[k]
                callback(state, m, element_schema, k)
            if model_name == 'NLINSERT':
                # special case - the NLINSERT generates a series of DRIFT and NLLENS elements
                _generate_nlinsert_elements(m, state, callback)


_QUOTED_MADX_FIELD = ['ExtractorType', 'Propagator']


#TODO(pjm): derived from template.elegant
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
                if element_schema[1] in _QUOTED_MADX_FIELD:
                    value = '"{}"'.format(value)
                state['lattice'] += '{}={},'.format(field_name, value)
    else:
        state['field_index'] = 0
        # NLINSERT is a special expanded element, show as a comment
        prefix = '! ' if model['type'] == 'NLINSERT' else ''
        _append_to_lattice(state, '{}{}: {},'.format(prefix, model['name'].upper(), model['type']))
        state['beamline_map'][model['_id']] = model['name']


#TODO(pjm): from template.elegant
def _model_name_for_data(model):
    return 'command_{}'.format(model['_type']) if '_type' in model else model['type']


def _nlinsert_name(model, el_name):
    return '{}.NLINSERT.{}'.format(model['name'], el_name).upper()


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


def _simulation_files(data):
    res = []
    bunch = data.models.bunch
    if bunch.distribution == 'file':
        res.append(template_common.lib_file_name('bunch', 'particleFile', bunch.particleFile))
    return res


def _sort_beamlines_by_length(lines):
    res = []
    for name in lines:
        res.append([name, len(lines[name])])
    return list(reversed(sorted(res, key=lambda v: v[1])))


def _validate_data(data, schema):
    # ensure enums match, convert ints/floats, apply scaling
    enum_info = template_common.validate_models(data, schema)
    for m in data['models']['elements']:
        template_common.validate_model(m, schema['model'][_model_name_for_data(m)], enum_info)
