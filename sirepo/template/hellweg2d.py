# -*- coding: utf-8 -*-
u"""Hellweg2D execution template.

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from __future__ import absolute_import, division, print_function
from pykern import pkcollections
from pykern import pkio
from pykern import pkjinja
from pykern.pkdebug import pkdc, pkdp
from sirepo import simulation_db
from sirepo.template import template_common, hellweg2d_dump_reader
import numpy
import os.path

HELLWEG2D_DUMP_FILE = 'all-data.bin'

#: Simulation type
SIM_TYPE = 'hellweg2d'

WANT_BROWSER_FRAME_CACHE = True


def background_percent_complete(report, run_dir, is_running, schema):
    if is_running:
        return {
            'percentComplete': 0,
            'frameCount': 0,
        }
    dump_file = _dump_file(run_dir)
    beam_header = hellweg2d_dump_reader.beam_header(dump_file)
    last_update_time = int(os.path.getmtime(dump_file))
    frame_count = beam_header.NPoints
    return {
        'lastUpdateTime': last_update_time,
        'percentComplete': 100,
        'frameCount': frame_count,
    }


def extract_beam_histrogram(report, run_dir, frame):
    beam_info = hellweg2d_dump_reader.beam_info(_dump_file(run_dir), frame)
    points = hellweg2d_dump_reader.get_points(beam_info, report.reportType)
    hist, edges = numpy.histogram(points, template_common.histogram_bins(report.histogramBins))
    return {
        'title': _report_title(report.reportType, simulation_db.get_schema(SIM_TYPE)['enum']['BeamHistogramReportType'], beam_info),
        'x_range': [edges[0], edges[-1]],
        'y_label': 'Number of Particles',
        'x_label': hellweg2d_dump_reader.get_label(report.reportType),
        'points': hist.T.tolist(),
        'frameCount': 1,
    }


def extract_beam_report(report, run_dir, frame):
    beam_info = hellweg2d_dump_reader.beam_info(_dump_file(run_dir), frame)
    x, y = report.reportType.split('-')
    data_list = [
        hellweg2d_dump_reader.get_points(beam_info, x),
        hellweg2d_dump_reader.get_points(beam_info, y),
    ]
    hist, edges = numpy.histogramdd(data_list, template_common.histogram_bins(report.histogramBins))
    return {
        'x_range': [float(edges[0][0]), float(edges[0][-1]), len(hist)],
        'y_range': [float(edges[1][0]), float(edges[1][-1]), len(hist[0])],
        'x_label': hellweg2d_dump_reader.get_label(x),
        'y_label': hellweg2d_dump_reader.get_label(y),
        'title': _report_title(report.reportType, simulation_db.get_schema(SIM_TYPE)['enum']['BeamReportType'], beam_info),
        'z_matrix': hist.T.tolist(),
        'z_label': 'Number of Particles',
    }


def fixup_old_data(data):
    pass


def get_animation_name(data):
    return 'animation'


def get_simulation_frame(run_dir, data, model_data):
    frame_index = int(data['frameIndex'])
    args = data['animationArgs'].split('_')
    return extract_beam_report(
        pkcollections.Dict({
            'reportType': args[0],
            'histogramBins': args[1],
        }),
        run_dir,
        frame_index,
    )


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
    return [
        r,
        'beam',
        'ellipticalDistribution',
        'energyPhaseDistribution',
        'solenoid',
        'sphericalDistribution',
        'twissDistribution',
    ]


def new_simulation(data, new_simulation_data):
    pass


def prepare_aux_files(run_dir, data):
    pass


def prepare_for_client(data):
    return data


def prepare_for_save(data):
    return data


def write_parameters(data, schema, run_dir, is_parallel):
    """Write the parameters file

    Args:
        data (dict): input
        schema (dict): to validate data
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


def _dump_file(run_dir):
    return os.path.join(str(run_dir), HELLWEG2D_DUMP_FILE)


def _generate_beam(models):
    # BEAM SPH2D 0.564 -15 5 NORM2D 0.30 0.0000001 90 180
    return 'BEAM {} {}'.format(_generate_transverse_dist(models), _generate_longitude_dist(models))


def _generate_charge(models):
    if models.beam.spaceCharge == 'none':
        return ''
    return 'SPCHARGE {}'.format(models.beam.spaceCharge.upper())


def _generate_current(models):
    return 'CURRENT {} {}'.format(models.beam.current, models.beam.numberOfParticles)


def _generate_longitude_dist(models):
    if models.beam.longitudinalDistribution == 'norm2d':
        dist = models.energyPhaseDistribution
        if models.energyPhaseDistribution.distributionType == 'uniform':
            return 'NORM2D {} {} {} {}'.format(
                dist.meanEnergy, dist.energySpread, dist.meanPhase, dist.phaseLength)
        if models.energyPhaseDistribution.distributionType == 'gaussian':
            return 'NORM2D {} {} {} {} {} {}'.format(
                dist.meanEnergy, dist.energySpread, dist.energyDeviation, dist.meanPhase, dist.phaseLength, dist.phaseDeviation)
        raise RuntimeError('unknown longitudinal distribution type: {}'.format(models.longitudinalDistribution.distributionType))
    raise RuntimeError('unknown longitudinal distribution: {}'.format(models.beam.longitudinalDistribution))


def _generate_parameters_file(data, run_dir=None, is_parallel=False):
    template_common.validate_models(data, simulation_db.get_schema(SIM_TYPE))
    v = template_common.flatten_data(data['models'], {})
    v['solenoidCommand'] = _generate_solenoid(data['models'])
    v['beamCommand'] = _generate_beam(data['models'])
    v['currentCommand'] = _generate_current(data['models'])
    v['chargeCommand'] = _generate_charge(data['models'])
    if is_parallel:
        #TODO(pjm): generate lattice
        v['latticeCommands'] = 'DRIFT 100.0 10.0 100' + "\n"
    else:
        # lattice element is required so make it very short and wide drift
        v['latticeCommands'] = 'DRIFT 1e-16 1e+16 2' + "\n"
    return pkjinja.render_resource('hellweg2d.py', v)


def _generate_solenoid(models):
    solenoid = models.solenoid
    if solenoid.sourceDefinition == 'none':
        return ''
    if solenoid.sourceDefinition == 'values':
        #TODO(pjm): latest version also has solenoid.fringeRegion
        return 'SOLENOID {} {} {}'.format(
            solenoid.fieldStrength, solenoid.length, solenoid.z0)
    raise RuntimeError('unknown solenoidDefinition: {}'.format(solenoid.solenoidDefinition))


def _generate_transverse_dist(models):
    dist_type = models.beam.transversalDistribution
    if dist_type == 'twiss4d':
        dist = models.twissDistribution
        return 'TWISS4D {} {} {} {} {} {}'.format(
            dist.horizontalAlpha, dist.horizontalBeta, dist.horizontalEmittance,
            dist.verticalAlpha, dist.verticalBeta, dist.verticalEmittance)
    if dist_type == 'sph2d':
        dist = models.sphericalDistribution
        curvature_factor = abs(dist.curvatureFactor)
        if dist.curvature == 'flat':
            curvature_factor = 0
        elif dist.curvature == 'concave':
            pass
        elif dist.curvature == 'convex':
            curvature_factor = -curvature_factor
        else:
            raise RuntimeError('unknown curvature: {}'.format(dist.curvature))
        return 'SPH2D {} {} {}'.format(dist.radialLimit, curvature_factor, dist.thermalEmittance)
    if dist_type == 'ell2d':
        dist = models.ellipticalDistribution
        return 'ELL2D {} {} {} {}'.format(dist.aX, dist.bY, dist.rotationAngle, dist.rmsDeviationFactor)
    raise RuntimeError('unknown transverse distribution: {}'.format(dist_type))


def _report_title(report_type, enum_values, beam_info):
    for e in enum_values:
        if e[0] == report_type:
            return '{}, z={} cm'.format(e[1], 100 * hellweg2d_dump_reader.get_parameter(beam_info, 'z'))
    raise RuntimeError('unknown report type: {}'.format(report_type))
