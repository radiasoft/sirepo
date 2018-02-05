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
import re

JSPEC_LOG_FILE = 'jspec.log'

SIM_TYPE = 'jspec'

WANT_BROWSER_FRAME_CACHE = True

_EMITTANCE_OUTPUT_FILENAME ='JSPEC.SDDS'

_ION_FILE_PREFIX = 'ions'

#TODO(pjm): fix units
_FIELD_LABEL = {
    'x': 'x [m]',
    'xp': "x' [rad]",
    'y': 'y [m]',
    'yp': "y' [rad]",
    't': 't [s]',
    'ds': 'ds [m]',
    'dp/p': 'dp/p [m]',
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


def background_percent_complete(report, run_dir, is_running, schema):
    files = _ion_files(run_dir)
    if is_running:
        current_step = _step_from_log(run_dir)
        data = simulation_db.read_json(run_dir.join(template_common.INPUT_BASE_NAME))
        settings = data.models.simulationSettings
        count = 0
        if len(files) > 1:
            count = len(files) - 1
        if current_step > 1:
            count = len(files)
        return {
            'percentComplete': 100 * current_step / settings.step_number,
            'frameCount': count,
        }
    if run_dir.join(_EMITTANCE_OUTPUT_FILENAME).exists():
        return {
            'percentComplete': 100,
            'frameCount': len(files),
        }
    return {
        'percentComplete': 0,
        'frameCount': 0,
    }


def fixup_old_data(data):
    pass


def get_animation_name(data):
    return 'animation'


def get_simulation_frame(run_dir, data, model_data):
    frame_index = int(data['frameIndex'])
    if data['modelName'] == 'emittanceAnimation':
        args = template_common.parse_animation_args(
            data,
            {
                '': ['x', 'y1', 'y2', 'y3', 'startTime'],
            },
        )
        return _extract_emittance_plot(args, run_dir)
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
    return template_common.filename_to_path([
        template_common.lib_file_name('ring', 'lattice', data['models']['ring']['lattice']),
    ], source_lib)


def models_related_to_report(data):
    if data['report'] == 'rateCalculationReport':
        return ['cooler', 'electronBeam', 'electronCoolingRate', 'intrabeamScatteringRate', 'ionBeam', 'ring']
    return []


def python_source_for_model(data, model):
    return '''
{}

with open('jspec.in', 'w') as f:
    f.write(jspec_file)

import os
os.system('jspec jspec.in')
    '''.format(_generate_parameters_file(data))


def remove_last_frame(run_dir):
    pass


def write_parameters(data, schema, run_dir, is_parallel):
    pkio.write_text(
        run_dir.join(template_common.PARAMETERS_PYTHON_FILE),
        _generate_parameters_file(data)
    )


def _extract_emittance_plot(report, run_dir):
    filename = str(run_dir.join(_EMITTANCE_OUTPUT_FILENAME))
    xfield = _map_field_name(report['x'])
    x, column_names, err = sdds_util.extract_sdds_column(filename, xfield, 0)
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
        'x_label': _field_label(xfield),
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
    v['emittanceOutputFilename'] = _EMITTANCE_OUTPUT_FILENAME
    v['runSimulation'] = report is None or report == 'animation'
    v['runRateCalculation'] = report is None or report == 'rateCalculationReport'
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


def _step_from_log(run_dir):
    log_file = run_dir.join(JSPEC_LOG_FILE)
    if log_file.exists():
        text = pkio.read_text(log_file)
        lines = text.split("\n")
        if len(lines) > 2:
            last_line = lines[-2]
            if re.search(r'^\d+$', last_line):
                return int(last_line) + 1
    return 1
