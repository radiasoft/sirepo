# -*- coding: utf-8 -*-
u"""JSPEC execution template.

:copyright: Copyright (c) 2017-2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkcollections
from pykern import pkio
from pykern import pkjinja
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdp
from sirepo import simulation_db
from sirepo.template import template_common, sdds_util
import glob
import math
import numpy as np
import os.path
import py.path
import re
import sdds
import sirepo.sim_data

_SIM_DATA, SIM_TYPE, _SCHEMA = sirepo.sim_data.template_globals()

JSPEC_INPUT_FILENAME = 'jspec.in'

JSPEC_LOG_FILE = 'jspec.log'

JSPEC_TWISS_FILENAME = 'jspec.tfs'

WANT_BROWSER_FRAME_CACHE = True

_BEAM_EVOLUTION_OUTPUT_FILENAME = 'JSPEC.SDDS'

_FORCE_TABLE_FILENAME = 'force_table.txt'

_ION_FILE_PREFIX = 'ions'

_FIELD_MAP = PKDict(
    emitx='emit_x',
    emity='emit_y',
    dpp='dp/p',
    sigmas='sigma_s',
    rxibs='rx_ibs',
    ryibs='ry_ibs',
    rsibs='rs_ibs',
    rxecool='rx_ecool',
    ryecool='ry_ecool',
    rsecool='rs_ecool',
    fx='f_x',
    flong='f_long',
    Vlong='V_long',
    Vtrans='V_trans',
    edensity='e_density',
)

#TODO(pjm): get this from the enum?
_FIELD_LABEL = PKDict(
    f_x='Transverse Force',
    f_long='Longitudinal Force',
    V_long='Longitudinal Velocity',
    V_trans='Transverse Velocity',
    e_density='Electron Density',
)

_OPTIONAL_MADX_TWISS_COLUMNS = ['NAME', 'TYPE', 'COUNT', 'DY', 'DPY']

_SPECIES_MASS_AND_CHARGE = PKDict(
    ALUMINUM=(25126.4878, 13),
    COPPER=(58603.6989, 29),
    DEUTERON=(1875.612928, 1),
    GOLD=(183432.7312, 79),
    HELIUM=(3755.675436, 2),
    LEAD=(193687.0203, 82),
    PROTON=(938.2720882, 1),
    RUTHENIUM=(94900.76612, 44),
    URANIUM=(221695.7759, 92),
    ZIRCONIUM=(83725.21758, 40),
)

_X_FIELD = 't'


def background_percent_complete(report, run_dir, is_running):
    if is_running:
        count, settings, has_rates = _background_task_info(run_dir)
        if settings.model == 'particle' and settings.save_particle_interval > 0:
            percent_complete = count * 100 / (1 + int(settings.time / settings.save_particle_interval))
            # the most recent file may not yet be fully written
            if count > 0:
                count -= 1
            return PKDict(
                percentComplete=percent_complete,
                frameCount=count,
                hasParticles=True,
                hasRates=has_rates,
            )
        else:
            # estimate the percent complete from the simulation time in sdds file
            if run_dir.join(_BEAM_EVOLUTION_OUTPUT_FILENAME).exists():
                return _beam_evolution_status(run_dir, settings, has_rates)
            return PKDict(
                percentComplete=0,
                frameCount=0,
            )
    if run_dir.join(_BEAM_EVOLUTION_OUTPUT_FILENAME).exists():
        count, settings, has_rates = _background_task_info(run_dir)
        has_force_table = run_dir.join(_FORCE_TABLE_FILENAME).exists()
        if count:
            return PKDict(
                percentComplete=100,
                frameCount=count,
                hasParticles=True,
                hasRates=has_rates,
                hasForceTable=has_force_table,
            )
        return PKDict(
            percentComplete=100,
            frameCount=1,
            hasRates=has_rates,
            hasForceTable=has_force_table,
        )
    return PKDict(
        percentComplete=0,
        frameCount=0,
    )


def get_application_data(data, **kwargs):
    if data.method == 'get_elegant_sim_list':
        tp = _SIM_DATA.jspec_elegant_twiss_path()
        res = []
        for f in pkio.sorted_glob(
            _SIM_DATA.jspec_elegant_dir().join('*', tp),
        ):
            assert str(f).endswith(tp)
            i = simulation_db.sid_from_compute_file(f)
            try:
                name = simulation_db.read_json(
                    simulation_db.sim_data_file('elegant', i),
                ).models.simulation.name
                res.append(PKDict(simulationId=i, name=name))
            except IOError:
                # ignore errors reading corrupted elegant sim files
                pass
        return {
            'simList': res,
        }
    elif data.method == 'compute_particle_ranges':
        return template_common.compute_field_range(data, _compute_range_across_files)
    assert False, 'unknown application data method={}'.format(data.method)


def get_data_file(run_dir, model, frame, options=None, **kwargs):
    if model in ('beamEvolutionAnimation', 'coolingRatesAnimation'):
        path = run_dir.join(_BEAM_EVOLUTION_OUTPUT_FILENAME)
    elif model == 'forceTableAnimation':
        path = run_dir.join(_FORCE_TABLE_FILENAME)
    else:
        path = py.path.local(_ion_files(run_dir)[frame])
    with open(str(path)) as f:
        return path.basename, f.read(), 'application/octet-stream'


def python_source_for_model(data, model):
    ring = data.models.ring
    elegant_twiss_file = None
    if ring.latticeSource == 'elegant':
        elegant_twiss_file = _SIM_DATA.lib_file_name_with_model_field('ring', 'elegantTwiss', ring.elegantTwiss)
    elif  ring.latticeSource == 'elegant-sirepo':
        elegant_twiss_file = _SIM_DATA.JSPEC_ELEGANT_TWISS_FILENAME
    convert_twiss_to_tfs = ''
    if elegant_twiss_file:
        convert_twiss_to_tfs = '''
from pykern import pkconfig
pkconfig.append_load_path('sirepo')
from sirepo.template import sdds_util
sdds_util.twiss_to_madx('{}', '{}')
        '''.format(elegant_twiss_file, JSPEC_TWISS_FILENAME)
    return '''
{}

with open('{}', 'w') as f:
    f.write(jspec_file)
{}
import os
os.system('jspec {}')
    '''.format(_generate_parameters_file(data), JSPEC_INPUT_FILENAME, convert_twiss_to_tfs, JSPEC_INPUT_FILENAME)


def remove_last_frame(run_dir):
    pass


def sim_frame_beamEvolutionAnimation(frame_args):
    return _sdds_report(
        frame_args,
        str(frame_args.run_dir.join(_BEAM_EVOLUTION_OUTPUT_FILENAME)),
        _X_FIELD,
    )


sim_frame_coolingRatesAnimation = sim_frame_beamEvolutionAnimation


def sim_frame_forceTableAnimation(frame_args):
    return _sdds_report(
        frame_args,
        str(frame_args.run_dir.join(_FORCE_TABLE_FILENAME)),
        frame_args.x,
    )


def sim_frame_particleAnimation(frame_args):
    page_index = frame_args.frameIndex
    xfield = _map_field_name(frame_args.x)
    yfield = _map_field_name(frame_args.y)
    filename = _ion_files(frame_args.run_dir)[page_index]
    data = frame_args.sim_in
    settings = data.models.simulationSettings
    time = settings.time / settings.step_number * settings.save_particle_interval * page_index
    if time > settings.time:
        time = settings.time
    x_col = sdds_util.extract_sdds_column(filename, xfield, 0)
    if x_col.err:
        return x_col.err
    x = x_col['values']
    y_col = sdds_util.extract_sdds_column(filename, yfield, 0)
    if y_col.err:
        return y_col.err
    y = y_col['values']
    model = data.models.particleAnimation
    model.update(frame_args)
    return template_common.heatmap([x, y], model, {
        'x_label': _field_label(xfield, x_col.column_def),
        'y_label': _field_label(yfield, y_col.column_def),
        'title': 'Ions at time {:.2f} [s]'.format(time),
    })


def validate_file(file_type, path):
    if file_type == 'ring-elegantTwiss':
        return None
    assert file_type == 'ring-lattice'
    for line in pkio.read_text(str(path)).split("\n"):
        # mad-x twiss column header starts with '*'
        match = re.search('^\*\s+(.*?)\s*$', line)
        if match:
            columns = re.split(r'\s+', match.group(1))
            is_ok = True
            for col in sdds_util.MADX_TWISS_COLUMS:
                if col in _OPTIONAL_MADX_TWISS_COLUMNS:
                    continue
                if col not in columns:
                    is_ok = False
                    break
            if is_ok:
                return None
    return 'TFS file must contain columns: {}'.format(', '.join(sdds_util.MADX_TWISS_COLUMS))


def write_parameters(data, run_dir, is_parallel):
    pkio.write_text(
        run_dir.join(template_common.PARAMETERS_PYTHON_FILE),
        _generate_parameters_file(data)
    )


def _background_task_info(run_dir):
    files = _ion_files(run_dir)
    data = simulation_db.read_json(run_dir.join(template_common.INPUT_BASE_NAME))
    settings = data.models.simulationSettings
    has_rates = settings.ibs == '1' or settings.e_cool == '1'
    return len(files), settings, has_rates


def _beam_evolution_status(run_dir, settings, has_rates):
    try:
        filename = str(run_dir.join(_BEAM_EVOLUTION_OUTPUT_FILENAME))
        col = sdds_util.extract_sdds_column(filename, 't', 0)
        t_max = max(col['values'])
        if t_max and settings.time > 0:
            return {
                # use current time as frameCount for uniqueness until simulation is completed
                'frameCount': int(float(os.path.getmtime(filename))),
                'percentComplete': 100.0 * t_max / settings.time,
                'hasRates': has_rates,
            }
    except Exception:
        pass
    return {
        'frameCount': 0,
        'percentComplete': 0,
    }


def _compute_range_across_files(run_dir, data):
    res = PKDict({
        _X_FIELD: [],
    })
    for v in _SCHEMA.enum.BeamColumn:
        res[_map_field_name(v[0])] = []
    for v in _SCHEMA.enum.CoolingRatesColumn:
        res[_map_field_name(v[0])] = []
    sdds_util.process_sdds_page(str(run_dir.join(_BEAM_EVOLUTION_OUTPUT_FILENAME)), 0, _compute_sdds_range, res)
    if run_dir.join(_FORCE_TABLE_FILENAME).exists():
        res2 = PKDict()
        for v in _SCHEMA.enum.ForceTableColumn:
            res2[_map_field_name(v[0])] = []
            sdds_util.process_sdds_page(str(run_dir.join(_FORCE_TABLE_FILENAME)), 0, _compute_sdds_range, res2)
        res.update(res2)
    #TODO(pjm): particleAnimation dp/p collides with beamEvolutionAnimation dp/p
    ion_files = _ion_files(run_dir)
    if len(ion_files):
        res2 = PKDict()
        for v in _SCHEMA.enum.ParticleColumn:
            res2[_map_field_name(v[0])] = []
        for filename in ion_files:
            sdds_util.process_sdds_page(filename, 0, _compute_sdds_range, res2)
        res.update(res2)
    # reverse field mapping back to enum values
    for k in _FIELD_MAP:
        v = _FIELD_MAP[k]
        if v in res:
            res[k] = res[v]
            del res[v]
    return res


def _compute_sdds_range(res, sdds_index=0):
    column_names = sdds.sddsdata.GetColumnNames(sdds_index)
    for field in res:
        values = sdds.sddsdata.GetColumn(sdds_index, column_names.index(field))
        if len(res[field]):
            res[field][0] = _safe_sdds_value(min(min(values), res[field][0]))
            res[field][1] = _safe_sdds_value(max(max(values), res[field][1]))
        else:
            res[field] = [_safe_sdds_value(min(values)), _safe_sdds_value(max(values))]


def _field_description(field, data):
    if not re.search(r'rx|ry|rs', field):
        return ''
    settings = data.models.simulationSettings
    ibs = settings.ibs == '1'
    e_cool = settings.e_cool == '1'
    dir = _field_direction(field)
    if 'ibs' in field:
        return ' - {} IBS rate'.format(dir)
    if 'ecool' in field:
        return ' - {} electron cooling rate'.format(dir)
    if ibs and e_cool:
        return ' - combined electron cooling and IBS heating rate ({})'.format(dir)
    if e_cool:
        return ' - {} electron cooling rate'.format(dir)
    if ibs:
        return ' - {} IBS rate'.format(dir)
    return ''


def _field_direction(field):
    if 'rx' in field:
        return 'horizontal'
    if 'ry' in field:
        return 'vertical'
    if 'rs' in field:
        return 'longitudinal'
    assert False, 'invalid direction field: {}'.format(field)


def _field_label(field, field_def):
    units = field_def[1]
    field = _FIELD_LABEL.get(field, field)
    if units == 'NULL':
        return field
    return '{} [{}]'.format(field, units)


def _generate_parameters_file(data):
    report = data.report if 'report' in data else None
    _set_mass_and_charge(data.models.ionBeam)
    template_common.validate_models(data, simulation_db.get_schema(SIM_TYPE))
    v = template_common.flatten_data(data.models, PKDict())
    v.beamEvolutionOutputFilename = _BEAM_EVOLUTION_OUTPUT_FILENAME
    v.runSimulation = report is None or report == 'animation'
    v.runRateCalculation = report is None or report == 'rateCalculationReport'
    if data.models.ring.latticeSource == 'madx':
        v.latticeFilename = _SIM_DATA.lib_file_name_with_model_field('ring', 'lattice', v.ring_lattice)
    else:
        v.latticeFilename = JSPEC_TWISS_FILENAME
    if v.ionBeam_beam_type == 'continuous':
        v.ionBeam_rms_bunch_length = 0
    v.simulationSettings_ibs = 'on' if v.simulationSettings_ibs == '1' else 'off'
    v.simulationSettings_e_cool = 'on' if v.simulationSettings_e_cool == '1' else 'off'
    return template_common.render_jinja(SIM_TYPE, v)


def _ion_files(run_dir):
    # sort files by file number suffix
    res = []
    for f in glob.glob(str(run_dir.join('{}*'.format(_ION_FILE_PREFIX)))):
        m = re.match(r'^.*?(\d+)\.txt$', f)
        if m:
            res.append([f, int(m.group(1))])
    return [v[0] for v in sorted(res, key=lambda v: v[1])]


def _map_field_name(f):
    return _FIELD_MAP.get(f, f)


def _resort_vtrans(x, plots):
    # special case - the force_table.txt vTrans is not sequential
    x = np.array(x)
    sort_idx = np.argsort(x)
    for p in plots:
        p.points = np.array(p.points)[sort_idx].tolist()
    return x[sort_idx].tolist()


def _safe_sdds_value(v):
    if isinstance(v, float) and (math.isinf(v) or math.isnan(v)):
        return 0
    return v


def _sdds_report(frame_args, filename, x_field):
    xfield = _map_field_name(x_field)
    x_col = sdds_util.extract_sdds_column(filename, xfield, 0)
    if x_col.err:
        return x_col.err
    x = x_col['values']
    if 'fieldRange' in frame_args.sim_in.models.particleAnimation:
        frame_args.fieldRange = frame_args.sim_in.models.particleAnimation.fieldRange
    plots = []
    for f in ('y1', 'y2', 'y3'):
        if f not in frame_args or frame_args[f] == 'none':
            continue
        yfield = _map_field_name(frame_args[f])
        y_col = sdds_util.extract_sdds_column(filename, yfield, 0)
        if y_col.err:
            return y_col.err
        y = y_col['values']
        label_prefix = ''
        #TODO(pjm): the forceScale feature makes the code unmanageable
        # it might be simpler if this was done on the client
        if 'forceScale' in frame_args \
           and yfield in ('f_x', 'f_long') \
           and frame_args.forceScale == 'negative':
            y = [-v for v in y]
            label_prefix = '-'
            if 'fieldRange' in frame_args:
                r = frame_args.fieldRange[frame_args[f]]
                frame_args.fieldRange[frame_args[f]] = [-r[1], -r[0]]
        plots.append(PKDict(
            field=frame_args[f],
            points=y,
            label='{}{}{}'.format(
                label_prefix,
                _field_label(yfield, y_col.column_def),
                _field_description(yfield, frame_args.sim_in),
            ),
        ))
    if xfield == 'V_trans':
        x = _resort_vtrans(x, plots)
    frame_args.x = x_field
    return template_common.parameter_plot(x, plots, frame_args, PKDict(
        y_label='',
        x_label=_field_label(xfield, x_col.column_def),
    ))


def _set_mass_and_charge(ion_beam):
    if ion_beam.particle != 'OTHER':
        ion_beam.mass, ion_beam.charge_number = _SPECIES_MASS_AND_CHARGE[ion_beam.particle]
