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
from sirepo.template import template_common
import os.path
import py.path

#: Simulation type
SIM_TYPE = 'hellweg2d'


def fixup_old_data(data):
    pass


def models_related_to_report(data):
    """What models are required for this data['report']

    Args:
        data (dict): simulation
    Returns:
        list: Named models, model fields or values (dict, list) that affect report
    """
    r = data['report']
    return [
        r,
        'beam',
        'ellipticalDistribution',
        'energyPhaseDistribution',
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
    v['beamCommand'] = _generate_beam(data['models'])
    v['currentCommand'] = _generate_current(data['models'])
    v['chargeCommand'] = _generate_charge(data['models'])
    return pkjinja.render_resource('hellweg2d_beam.py', v)


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
