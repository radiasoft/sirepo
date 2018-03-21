# -*- coding: utf-8 -*-
u"""JSPEC execution template.

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from __future__ import absolute_import, division, print_function
from pykern import pkcollections
from pykern import pkio
from pykern import pkjinja
from pykern.pkdebug import pkdc, pkdp
from sirepo import simulation_db
from sirepo.template import template_common, sdds_util
import glob
import numpy as np
import os.path
import py.path
import re

ELEGANT_TWISS_FILENAME = 'twiss_output.filename.sdds'

JSPEC_INPUT_FILENAME = 'jspec.in'

JSPEC_LOG_FILE = 'jspec.log'

JSPEC_TWISS_FILENAME = 'jspec.tfs'

SIM_TYPE = 'jspec'

WANT_BROWSER_FRAME_CACHE = True

_BEAM_EVOLUTION_OUTPUT_FILENAME = 'JSPEC.SDDS'

_ELEGANT_TWISS_PATH = 'animation/{}'.format(ELEGANT_TWISS_FILENAME)

_ION_FILE_PREFIX = 'ions'

#TODO(pjm): fix units
_FIELD_LABEL = {
    'x': 'x [m]',
    'xp': "x' [rad]",
    'y': 'y [m]',
    'yp': "y' [rad]",
    't': 't [s]',
    'ds': 'ds [m]',
    'dp/p': 'dp/p',
    'emit_x': 'emit x [m*rad]',
    'emit_y': 'emit y [m*rad]',
    'sigma_s': 'sigma s [m]',
    'rx': 'rx [1/s]',
    'ry': 'ry [1/s]',
    'rs': 'rs [1/s]',
}

_FIELD_MAP = {
    'emitx': 'emit_x',
    'emity': 'emit_y',
    'dpp': 'dp/p',
    'sigmas': 'sigma_s',
}

_PLOT_LINE_COLOR = {
    'y1': '#1f77b4',
    'y2': '#ff7f0e',
    'y3': '#2ca02c',
}

_SCHEMA = simulation_db.get_schema(SIM_TYPE)

_X_FIELD = 't'


def background_percent_complete(report, run_dir, is_running, schema):
    if is_running:
        data = simulation_db.read_json(run_dir.join(template_common.INPUT_BASE_NAME))
        settings = data.models.simulationSettings
        percent_complete = 0

        if settings.model == 'particle' and settings.save_particle_interval > 0:
            files = _ion_files(run_dir)
            count = len(files)
            percent_complete = count * 100 / (1 + int(settings.time / settings.save_particle_interval))
            # the most recent file may not yet be fully written
            if count > 0:
                count -= 1
            return {
                'percentComplete': percent_complete,
                'frameCount': count,
                'hasParticles': True,
            }
        else:
            # estimate the percent complete from the simulation time in sdds file
            if run_dir.join(_BEAM_EVOLUTION_OUTPUT_FILENAME).exists():
                return _beam_evolution_status(run_dir, settings)
            return {
                'percentComplete': 0,
                'frameCount': 0,
            }
    if run_dir.join(_BEAM_EVOLUTION_OUTPUT_FILENAME).exists():
        files = _ion_files(run_dir)
        if len(files):
            return {
                'percentComplete': 100,
                'frameCount': len(files),
                'hasParticles': True,
            }
        else:
            return {
                'percentComplete': 100,
                'frameCount': 1,
            }
    return {
        'percentComplete': 0,
        'frameCount': 0,
    }


def fixup_old_data(data):
    template_common.update_model_defaults(data['models']['ring'], 'ring', _SCHEMA)
    if 'coolingRatesAnimation' not in data['models']:
        for m in ('beamEvolutionAnimation', 'coolingRatesAnimation'):
            data['models'][m] = {}
            template_common.update_model_defaults(data['models'][m], m, _SCHEMA)
    if 'beam_type' not in data['models']['ionBeam']:
        ion_beam = data['models']['ionBeam']
        ion_beam['beam_type'] = 'bunched' if ion_beam['rms_bunch_length'] > 0 else 'continuous'
    if 'beam_type' not in data['models']['electronBeam']:
        ebeam = data['models']['electronBeam']
        ebeam['beam_type'] = 'continuous' if ebeam['shape'] == 'dc_uniform' else 'bunched'
        ebeam['rh'] = ebeam['rv'] = 0.004
    settings = data['models']['simulationSettings']
    if settings['model'] == 'model_beam':
        settings['model'] = 'particle'
    if 'ibs' not in settings:
        settings['ibs'] = '1'
        settings['e_cool'] = '1'
    if 'ref_bet_x' not in settings or not settings['ref_bet_x']:
        settings['ref_bet_x'] = settings['ref_bet_y'] = 10
        for f in ('ref_alf_x', 'ref_disp_x', 'ref_disp_dx', 'ref_alf_y', 'ref_disp_y', 'ref_disp_dy'):
            settings[f] = 0


def get_animation_name(data):
    return 'animation'


def get_application_data(data):
    if data['method'] == 'get_elegant_sim_list':
        res = []
        for f in pkio.sorted_glob(_elegant_dir().join('*/', _ELEGANT_TWISS_PATH)):
            m = re.match(r'.*?/elegant/(.*?)/animation', str(f))
            if not m:
                continue
            id = m.group(1)
            name = simulation_db.read_json(_elegant_dir().join(id, '/', simulation_db.SIMULATION_DATA_FILE)).models.simulation.name
            res.append({
                'simulationId': id,
                'name': name,
            })
        return {
            'simList': res,
        }


def get_data_file(run_dir, model, frame, options=None):
    if model == 'beamEvolutionAnimation':
        path = run_dir.join(_BEAM_EVOLUTION_OUTPUT_FILENAME)
    else:
        path = py.path.local(_ion_files(run_dir)[frame])
    with open(str(path)) as f:
        return path.basename, f.read(), 'application/octet-stream'


def get_simulation_frame(run_dir, data, model_data):
    frame_index = int(data['frameIndex'])
    if data['modelName'] in ('beamEvolutionAnimation', 'coolingRatesAnimation'):
        args = template_common.parse_animation_args(
            data,
            {
                '1': ['x', 'y1', 'y2', 'y3', 'startTime'],
                '': ['y1', 'y2', 'y3', 'startTime'],
            },
        )
        return _extract_evolution_plot(args, run_dir)
    elif data['modelName'] == 'particleAnimation':
        args = template_common.parse_animation_args(
            data,
            {
                '': ['x', 'y', 'histogramBins', 'startTime'],
            },
        )
        return _extract_particle_plot(args, run_dir, frame_index)
    raise RuntimeError('unknown animation model: {}'.format(data['modelName']))



def lib_files(data, source_lib):
    res = []
    lattice_source = data['models']['ring']['latticeSource']
    if lattice_source == 'madx':
        res.append(template_common.lib_file_name('ring', 'lattice', data['models']['ring']['lattice']))
    elif lattice_source == 'elegant':
        res.append(template_common.lib_file_name('ring', 'elegantTwiss', data['models']['ring']['elegantTwiss']))
    return template_common.filename_to_path(res, source_lib)


def models_related_to_report(data):
    if data['report'] == 'rateCalculationReport':
        return ['cooler', 'electronBeam', 'electronCoolingRate', 'intrabeamScatteringRate', 'ionBeam', 'ring']
    return []


def python_source_for_model(data, model):
    return '''
{}

with open('{}', 'w') as f:
    f.write(jspec_file)

import os
os.system('jspec {}')
    '''.format(_generate_parameters_file(data), JSPEC_INPUT_FILENAME, JSPEC_INPUT_FILENAME)


def remove_last_frame(run_dir):
    pass


def write_parameters(data, schema, run_dir, is_parallel):
    _prepare_twiss_file(data, run_dir)
    pkio.write_text(
        run_dir.join(template_common.PARAMETERS_PYTHON_FILE),
        _generate_parameters_file(data)
    )


def _beam_evolution_status(run_dir, settings):
    try:
        filename = str(run_dir.join(_BEAM_EVOLUTION_OUTPUT_FILENAME))
        t, column_names, err = sdds_util.extract_sdds_column(filename, 't', 0)
        t_max = max(t)
        if t_max and settings.time > 0:
            return {
                'frameCount': int(float(os.path.getmtime(filename))),
                'percentComplete': 100.0 * t_max / settings.time,
            }
    except:
        pass
    return {
        'frameCount': 0,
        'percentComplete': 0,
    }


def _elegant_dir():
    return simulation_db.simulation_dir(SIM_TYPE).join('../elegant')


def _extract_evolution_plot(report, run_dir):
    filename = str(run_dir.join(_BEAM_EVOLUTION_OUTPUT_FILENAME))
    x, column_names, err = sdds_util.extract_sdds_column(filename, _X_FIELD, 0)
    if err:
        return err
    plots = []
    y_range = None
    for f in ('y1', 'y2', 'y3'):
        if report[f] == 'none':
            continue
        yfield = _map_field_name(report[f])
        y, _, err = sdds_util.extract_sdds_column(filename, yfield, 0)
        if err:
            return err
        if y_range:
            y_range[0] = min(y_range[0], min(y))
            y_range[1] = max(y_range[1], max(y))
        else:
            y_range = [min(y), max(y)]
        plots.append({
            'points': y,
            'label': _field_label(yfield),
            'color': _PLOT_LINE_COLOR[f],
        })
    return {
        'title': '',
        'x_range': [min(x), max(x)],
        'y_label': '',
        'x_label': _field_label(_X_FIELD),
        'x_points': x,
        'plots': plots,
        'y_range': y_range,
    }


def _extract_particle_plot(report, run_dir, page_index):
    xfield = _map_field_name(report['x'])
    yfield = _map_field_name(report['y'])
    bins = report['histogramBins']
    filename = _ion_files(run_dir)[page_index]
    data = simulation_db.read_json(run_dir.join(template_common.INPUT_BASE_NAME))
    settings = data.models.simulationSettings
    time = settings.time / settings.step_number * settings.save_particle_interval * page_index
    if time > settings.time:
        time = settings.time
    x, column_names, err = sdds_util.extract_sdds_column(filename, xfield, 0)
    if err:
        return err
    y, _, err = sdds_util.extract_sdds_column(filename, yfield, 0)
    if err:
        return err
    hist, edges = np.histogramdd([x, y], template_common.histogram_bins(bins))
    return {
        'x_range': [float(edges[0][0]), float(edges[0][-1]), len(hist)],
        'y_range': [float(edges[1][0]), float(edges[1][-1]), len(hist[0])],
        'x_label': _field_label(xfield),
        'y_label': _field_label(yfield),
        'title': 'Ions at time {:.2f} [s]'.format(time),
        'z_matrix': hist.T.tolist(),
    }


def _field_label(field):
    if field in _FIELD_LABEL:
        return _FIELD_LABEL[field]
    return field


def _generate_parameters_file(data):
    report = data['report'] if 'report' in data else None
    template_common.validate_models(data, simulation_db.get_schema(SIM_TYPE))
    v = template_common.flatten_data(data['models'], {})
    v['beamEvolutionOutputFilename'] = _BEAM_EVOLUTION_OUTPUT_FILENAME
    v['runSimulation'] = report is None or report == 'animation'
    v['runRateCalculation'] = report is None or report == 'rateCalculationReport'
    if data['models']['ring']['latticeSource'] == 'madx':
        v['latticeFilename'] = template_common.lib_file_name('ring', 'lattice', v['ring_lattice'])
    else:
        v['latticeFilename'] = JSPEC_TWISS_FILENAME
    if v['ionBeam_beam_type'] == 'continuous':
        v['ionBeam_rms_bunch_length'] = 0
    #TODO(pjm): work-around for recent JSPEC bug, remove when fixed
    # set simulationSettings.sample_number = electronCoolingRate.sample_number if greater
    if v['simulationSettings_sample_number'] > v['electronCoolingRate_sample_number']:
        v['simulationSettings_sample_number'] = v['electronCoolingRate_sample_number']
    v['simulationSettings_ibs'] = 'on' if int(v['simulationSettings_ibs']) else 'off'
    v['simulationSettings_e_cool'] = 'on' if int(v['simulationSettings_e_cool']) else 'off'
    return template_common.render_jinja(SIM_TYPE, v)


def _ion_files(run_dir):
    # sort files by file number suffix
    res = []
    for f in glob.glob(str(run_dir.join('{}*'.format(_ION_FILE_PREFIX)))):
        m = re.match(r'^.*?(\d+)\.txt$', f)
        if m:
            res.append([f, int(m.group(1))])
    return map(lambda v: v[0], sorted(res, key=lambda v: v[1]))


def _map_field_name(f):
    if f in _FIELD_MAP:
        return _FIELD_MAP[f]
    return f


def _prepare_twiss_file(data, run_dir):
    if data['models']['ring']['latticeSource'] == 'elegant-sirepo':
        sim_id = data['models']['ring']['elegantSirepo']
        if not sim_id:
            raise RuntimeError('elegant simulation not selected')
        f = _elegant_dir().join(sim_id, _ELEGANT_TWISS_PATH)
        if not f.exists():
            raise RuntimeError('elegant twiss output unavailable. Run elegant simulation.')
        f.copy(run_dir)
