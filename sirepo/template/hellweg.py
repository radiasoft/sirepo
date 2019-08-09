# -*- coding: utf-8 -*-
u"""Hellweg execution template.

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from __future__ import absolute_import, division, print_function
from pykern import pkcollections
from pykern import pkio
from pykern.pkdebug import pkdc, pkdp
from rslinac import solver
from sirepo import simulation_db
from sirepo.template import template_common, hellweg_dump_reader
import math
import numpy as np
import os.path
import py.path
import re

HELLWEG_DUMP_FILE = 'all-data.bin'

HELLWEG_SUMMARY_FILE = 'output.txt'

HELLWEG_INI_FILE = 'defaults.ini'

HELLWEG_INPUT_FILE = 'input.txt'

#: Simulation type
SIM_TYPE = 'hellweg'

WANT_BROWSER_FRAME_CACHE = True

# lattice element is required so make it very short and wide drift
_DEFAULT_DRIFT_ELEMENT = 'DRIFT 1e-16 1e+16 2' + "\n"

_HELLWEG_PARSED_FILE = 'PARSED.TXT'

_REPORT_STYLE_FIELDS = ['colorMap', 'notes']

_SCHEMA = simulation_db.get_schema(SIM_TYPE)

def background_percent_complete(report, run_dir, is_running):
    if is_running:
        return {
            'percentComplete': 0,
            'frameCount': 0,
        }
    dump_file = _dump_file(run_dir)
    if os.path.exists(dump_file):
        beam_header = hellweg_dump_reader.beam_header(dump_file)
        last_update_time = int(os.path.getmtime(dump_file))
        frame_count = beam_header.NPoints
        return {
            'lastUpdateTime': last_update_time,
            'percentComplete': 100,
            'frameCount': frame_count,
            'summaryData': _summary_text(run_dir),
        }
    return {
        'percentComplete': 100,
        'frameCount': 0,
        'error': _parse_error_message(run_dir)
    }


def extract_beam_histrogram(report, run_dir, frame):
    beam_info = hellweg_dump_reader.beam_info(_dump_file(run_dir), frame)
    points = hellweg_dump_reader.get_points(beam_info, report.reportType)
    hist, edges = np.histogram(points, template_common.histogram_bins(report.histogramBins))
    return {
        'title': _report_title(report.reportType, 'BeamHistogramReportType', beam_info),
        'x_range': [edges[0], edges[-1]],
        'y_label': 'Number of Particles',
        'x_label': hellweg_dump_reader.get_label(report.reportType),
        'points': hist.T.tolist(),
    }


def extract_beam_report(report, run_dir, frame):
    data = simulation_db.read_json(run_dir.join(template_common.INPUT_BASE_NAME))
    model = data.models.beamAnimation
    model.update(report)
    beam_info = hellweg_dump_reader.beam_info(_dump_file(run_dir), frame)
    x, y = report.reportType.split('-')
    values = [
        hellweg_dump_reader.get_points(beam_info, x),
        hellweg_dump_reader.get_points(beam_info, y),
    ]
    model['x'] = x
    model['y'] = y
    # see issue #872
    if not np.any(values):
        values = [[], []]
    return template_common.heatmap(values, model, {
        'x_label': hellweg_dump_reader.get_label(x),
        'y_label': hellweg_dump_reader.get_label(y),
        'title': _report_title(report.reportType, 'BeamReportType', beam_info),
        'z_label': 'Number of Particles',
        'summaryData': _summary_text(run_dir),
    })


def extract_parameter_report(report, run_dir):
    s = solver.BeamSolver(
        os.path.join(str(run_dir), HELLWEG_INI_FILE),
        os.path.join(str(run_dir), HELLWEG_INPUT_FILE))
    s.load_bin(os.path.join(str(run_dir), HELLWEG_DUMP_FILE))
    y1_var, y2_var = report.reportType.split('-')
    x_field = 'z'
    x = s.get_structure_parameters(_parameter_index(x_field))
    y1 = s.get_structure_parameters(_parameter_index(y1_var))
    y1_extent = [np.min(y1), np.max(y1)]
    y2 = s.get_structure_parameters(_parameter_index(y2_var))
    y2_extent = [np.min(y2), np.max(y2)]
    return {
        'title': _enum_text('ParameterReportType', report.reportType),
        'x_range': [x[0], x[-1]],
        'y_label': hellweg_dump_reader.get_parameter_label(y1_var),
        'x_label': hellweg_dump_reader.get_parameter_label(x_field),
        'x_points': x,
        'points': [
            y1,
            y2,
        ],
        'y_range': [min(y1_extent[0], y2_extent[0]), max(y1_extent[1], y2_extent[1])],
        'y1_title': hellweg_dump_reader.get_parameter_title(y1_var),
        'y2_title': hellweg_dump_reader.get_parameter_title(y2_var),
    }


def extract_particle_report(report, run_dir):
    x_field = 'z0'
    particle_info = hellweg_dump_reader.particle_info(_dump_file(run_dir), report.reportType, int(report.renderCount))
    x = particle_info['z_values']
    return {
        'title': _enum_text('ParticleReportType', report.reportType),
        'x_range': [np.min(x), np.max(x)],
        'y_label': hellweg_dump_reader.get_label(report.reportType),
        'x_label': hellweg_dump_reader.get_label(x_field),
        'x_points': x,
        'points': particle_info['y_values'],
        'y_range': particle_info['y_range'],
    }


def fixup_old_data(data):
    for m in ('beamAnimation', 'beamHistogramAnimation', 'parameterAnimation', 'particleAnimation'):
        if m not in data.models:
            data.models[m] = pkcollections.Dict({})
        template_common.update_model_defaults(data.models[m], m, _SCHEMA)
    if 'solenoidFile' not in data['models']['solenoid']:
        data['models']['solenoid']['solenoidFile'] = ''
    if 'beamDefinition' not in data['models']['beam']:
        beam = data['models']['beam']
        beam['beamDefinition'] = 'transverse_longitude'
        beam['cstCompress'] = '0'
        beam['transversalFile2d'] = ''
        beam['transversalFile4d'] = ''
        beam['longitudinalFile1d'] = ''
        beam['longitudinalFile2d'] = ''
        beam['cstFile'] = ''
    template_common.organize_example(data)


def get_animation_name(data):
    return 'animation'


def get_application_data(data):
    if data['method'] == 'compute_particle_ranges':
        return template_common.compute_field_range(data, _compute_range_across_files)
    assert False, 'unknown application data method: {}'.format(data['method'])


def lib_files(data, source_lib):
    return template_common.filename_to_path(_simulation_files(data), source_lib)


def get_simulation_frame(run_dir, data, model_data):
    frame_index = int(data['frameIndex'])
    if data['modelName'] == 'beamAnimation':
        args = template_common.parse_animation_args(
            data,
            {
                '1': ['reportType', 'histogramBins', 'startTime'],
                '': ['reportType', 'histogramBins', 'plotRangeType', 'horizontalSize', 'horizontalOffset', 'verticalSize', 'verticalOffset', 'isRunning', 'startTime'],
            },
        )
        return extract_beam_report(args, run_dir, frame_index)
    elif data['modelName'] == 'beamHistogramAnimation':
        args = template_common.parse_animation_args(
            data,
            {'': ['reportType', 'histogramBins', 'startTime']},
        )
        return extract_beam_histrogram(args, run_dir, frame_index)
    elif data['modelName'] == 'particleAnimation':
        args = template_common.parse_animation_args(
            data,
            {'': ['reportType', 'renderCount', 'startTime']},
        )
        return extract_particle_report(args, run_dir)
    elif data['modelName'] == 'parameterAnimation':
        args = template_common.parse_animation_args(
            data,
            {'': ['reportType', 'startTime']},
        )
        return extract_parameter_report(args, run_dir)
    raise RuntimeError('unknown animation model: {}'.format(data['modelName']))


def models_related_to_report(data):
    """What models are required for this data['report']

    Args:
        data (dict): simulation
    Returns:
        list: Named models, model fields or values (dict, list) that affect report
    """
    r = data['report']
    if r == 'animation':
        return []
    res = template_common.report_fields(data, r, _REPORT_STYLE_FIELDS) + [
        'beam',
        'ellipticalDistribution',
        'energyPhaseDistribution',
        'solenoid',
        'sphericalDistribution',
        'twissDistribution',
    ]
    for f in template_common.lib_files(data):
        res.append(f.mtime())
    return res


def python_source_for_model(data, model):
    return '''
from rslinac import solver

{}

with open('input.txt', 'w') as f:
    f.write(input_file)

with open('defaults.ini', 'w') as f:
    f.write(ini_file)

s = solver.BeamSolver('defaults.ini', 'input.txt')
s.solve()
s.save_output('output.txt')
    '''.format(_generate_parameters_file(data, is_parallel=len(data.models.beamline)))


def remove_last_frame(run_dir):
    pass


def validate_delete_file(data, filename, file_type):
    """Returns True if the filename is in use by the simulation data."""
    return filename in _simulation_files(data)


def write_parameters(data, run_dir, is_parallel):
    """Write the parameters file

    Args:
        data (dict): input
        run_dir (py.path): where to write
        is_parallel (bool): run in background?
    """
    pkio.write_text(
        run_dir.join(template_common.PARAMETERS_PYTHON_FILE),
        _generate_parameters_file(
            data,
            run_dir,
            is_parallel,
        ),
    )


def _compute_range_across_files(run_dir, data):
    res = {}
    for v in _SCHEMA.enum.BeamReportType:
        x, y = v[0].split('-')
        res[x] = []
        res[y] = []
    dump_file = _dump_file(run_dir)
    if not os.path.exists(dump_file):
        return res
    beam_header = hellweg_dump_reader.beam_header(dump_file)
    for frame in xrange(beam_header.NPoints):
        beam_info = hellweg_dump_reader.beam_info(dump_file, frame)
        for field in res:
            values = hellweg_dump_reader.get_points(beam_info, field)
            if not len(values):
                pass
            elif len(res[field]):
                res[field][0] = min(min(values), res[field][0])
                res[field][1] = max(max(values), res[field][1])
            else:
                res[field] = [min(values), max(values)]
    return res


def _dump_file(run_dir):
    return os.path.join(str(run_dir), HELLWEG_DUMP_FILE)


def _enum_text(enum_name, v):
    enum_values = _SCHEMA['enum'][enum_name]
    for e in enum_values:
        if e[0] == v:
            return e[1]
    raise RuntimeError('invalid enum value: {}, {}'.format(enum_values, v))


def _generate_beam(models):
    # BEAM SPH2D 0.564 -15 5 NORM2D 0.30 0.0000001 90 180
    beam_def = models.beam.beamDefinition
    if beam_def == 'transverse_longitude':
        return 'BEAM {} {}'.format(_generate_transverse_dist(models), _generate_longitude_dist(models))
    if beam_def == 'cst_pit':
        return 'BEAM CST_PIT {} {}'.format(
            template_common.lib_file_name('beam', 'cstFile', models.beam.cstFile),
            'COMPRESS' if models.beam.cstCompress else '',
        )
    if beam_def == 'cst_pid':
        return 'BEAM CST_PID {} {}'.format(
            template_common.lib_file_name('beam', 'cstFile', models.beam.cstFile),
            _generate_energy_phase_distribution(models.energyPhaseDistribution),
        )
    raise RuntimeError('invalid beam def: {}'.format(beam_def))


def _generate_cell_params(el):
    #TODO(pjm): add an option field to select auto-calculate
    if el.attenuation == 0 and el.aperture == 0:
        return '{} {} {}'.format(el.phaseAdvance, el.phaseVelocity, el.acceleratingInvariant)
    return '{} {} {} {} {}'.format(el.phaseAdvance, el.phaseVelocity, el.acceleratingInvariant, el.attenuation, el.aperture)


def _generate_charge(models):
    if models.beam.spaceCharge == 'none':
        return ''
    return 'SPCHARGE {} {}'.format(models.beam.spaceCharge.upper(), models.beam.spaceChargeCore)


def _generate_current(models):
    return 'CURRENT {} {}'.format(models.beam.current, models.beam.numberOfParticles)


def _generate_energy_phase_distribution(dist):
    return '{} {} {}'.format(
        dist.meanPhase,
        dist.phaseLength,
        dist.phaseDeviation if dist.distributionType == 'gaussian' else '',
    )


def _generate_lattice(models):
    res = ''
    for el in models.beamline:
        if el.type == 'powerElement':
            res += 'POWER {} {} {}'.format(el.inputPower, el.frequency, el.phaseShift)
        elif el.type == 'cellElement':
            res += 'CELL {}'.format(_generate_cell_params(el))
            has_cell_or_drift = True
        elif el.type == 'cellsElement':
            res += 'CELLS {} {}'.format(el.repeat, _generate_cell_params(el))
            has_cell_or_drift = True
        elif el.type == 'driftElement':
            res += 'DRIFT {} {} {}'.format(el.length, el.radius, el.meshPoints)
            has_cell_or_drift = True
        elif el.type == 'saveElement':
            #TODO(pjm): implement this
            pass
        else:
            raise RuntimeError('unknown element type: {}'.format(el.type))
        res += "\n"
    return res


def _generate_longitude_dist(models):
    dist_type = models.beam.longitudinalDistribution
    if dist_type == 'norm2d':
        dist = models.energyPhaseDistribution
        if dist.distributionType == 'uniform':
            return 'NORM2D {} {} {} {}'.format(
                dist.meanEnergy, dist.energySpread, dist.meanPhase, dist.phaseLength)
        if dist.distributionType == 'gaussian':
            return 'NORM2D {} {} {} {} {} {}'.format(
                dist.meanEnergy, dist.energySpread, dist.energyDeviation, dist.meanPhase, dist.phaseLength, dist.phaseDeviation)
        raise RuntimeError('unknown longitudinal distribution type: {}'.format(models.longitudinalDistribution.distributionType))
    if dist_type == 'file1d':
        return 'FILE1D {} {}'.format(
            template_common.lib_file_name('beam', 'longitudinalFile1d', models.beam.longitudinalFile1d),
            _generate_energy_phase_distribution(models.energyPhaseDistribution),
        )
    if dist_type == 'file2d':
        return 'FILE2D {}'.format(template_common.lib_file_name('beam', 'transversalFile2d', beam.transversalFile2d))

    raise RuntimeError('unknown longitudinal distribution: {}'.format(models.beam.longitudinalDistribution))


def _generate_options(models):
    if models.simulationSettings.allowBackwardWaves == '1':
        return 'OPTIONS REVERSE'
    return ''


def _generate_parameters_file(data, run_dir=None, is_parallel=False):
    template_common.validate_models(data, _SCHEMA)
    v = template_common.flatten_data(data['models'], {})
    v['optionsCommand'] = _generate_options(data['models'])
    v['solenoidCommand'] = _generate_solenoid(data['models'])
    v['beamCommand'] = _generate_beam(data['models'])
    v['currentCommand'] = _generate_current(data['models'])
    v['chargeCommand'] = _generate_charge(data['models'])
    if is_parallel:
        v['latticeCommands'] = _generate_lattice(data['models'])
    else:
        v['latticeCommands'] = _DEFAULT_DRIFT_ELEMENT
    return template_common.render_jinja(SIM_TYPE, v)


def _generate_solenoid(models):
    solenoid = models.solenoid
    if solenoid.sourceDefinition == 'none':
        return ''
    if solenoid.sourceDefinition == 'values':
        #TODO(pjm): latest version also has solenoid.fringeRegion
        return 'SOLENOID {} {} {}'.format(
            solenoid.fieldStrength, solenoid.length, solenoid.z0)
    if solenoid.sourceDefinition == 'file':
        return 'SOLENOID {}'.format(
            template_common.lib_file_name('solenoid', 'solenoidFile', solenoid.solenoidFile))
    raise RuntimeError('unknown solenoidDefinition: {}'.format(solenoid.sourceDefinition))


def _generate_transverse_dist(models):
    dist_type = models.beam.transversalDistribution
    if dist_type == 'twiss4d':
        dist = models.twissDistribution
        return 'TWISS4D {} {} {} {} {} {}'.format(
            dist.horizontalAlpha, dist.horizontalBeta, dist.horizontalEmittance,
            dist.verticalAlpha, dist.verticalBeta, dist.verticalEmittance)
    if dist_type == 'sph2d':
        dist = models.sphericalDistribution
        if dist.curvature == 'flat':
            dist.curvatureFactor = 0
        return 'SPH2D {} {} {}'.format(dist.radialLimit, dist.curvatureFactor, dist.thermalEmittance)
    if dist_type == 'ell2d':
        dist = models.ellipticalDistribution
        return 'ELL2D {} {} {} {}'.format(dist.aX, dist.bY, dist.rotationAngle, dist.rmsDeviationFactor)
    beam = models.beam
    if dist_type == 'file2d':
        return 'FILE2D {}'.format(template_common.lib_file_name('beam', 'transversalFile2d', beam.transversalFile2d))
    if dist_type == 'file4d':
        return 'FILE4D {}'.format(template_common.lib_file_name('beam', 'transversalFile4d', beam.transversalFile4d))
    raise RuntimeError('unknown transverse distribution: {}'.format(dist_type))


def _parameter_index(name):
    return hellweg_dump_reader.parameter_index(name)


def _parse_error_message(run_dir):
    path = os.path.join(str(run_dir), _HELLWEG_PARSED_FILE)
    if not os.path.exists(path):
        return 'No elements generated'
    text = pkio.read_text(str(path))
    for line in text.split("\n"):
        match = re.search('^ERROR:\s(.*)$', line)
        if match:
            return match.group(1)
    return 'No output generated'


def _report_title(report_type, enum_name, beam_info):
    return '{}, z={:.4f} cm'.format(
        _enum_text(enum_name, report_type),
        100 * hellweg_dump_reader.get_parameter(beam_info, 'z'))


def _simulation_files(data):
    res = []
    solenoid = data.models.solenoid
    if solenoid.sourceDefinition == 'file' and solenoid.solenoidFile:
        res.append(template_common.lib_file_name('solenoid', 'solenoidFile', solenoid.solenoidFile))
    beam = data.models.beam
    if beam.beamDefinition == 'cst_pit' or beam.beamDefinition == 'cst_pid':
        res.append(template_common.lib_file_name('beam', 'cstFile', beam.cstFile))
    if beam.beamDefinition == 'transverse_longitude':
        if beam.transversalDistribution == 'file2d':
            res.append(template_common.lib_file_name('beam', 'transversalFile2d', beam.transversalFile2d))
        elif beam.transversalDistribution == 'file4d':
            res.append(template_common.lib_file_name('beam', 'transversalFile4d', beam.transversalFile4d))
        if beam.longitudinalDistribution == 'file1d':
            res.append(template_common.lib_file_name('beam', 'longitudinalFile1d', beam.longitudinalFile1d))
        if beam.longitudinalDistribution == 'file2d':
            res.append(template_common.lib_file_name('beam', 'longitudinalFile2d', beam.longitudinalFile2d))
    return res


def _summary_text(run_dir):
    return pkio.read_text(os.path.join(str(run_dir), HELLWEG_SUMMARY_FILE))
