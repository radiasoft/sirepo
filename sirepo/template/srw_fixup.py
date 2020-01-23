# -*- coding: utf-8 -*-
u"""SRW template fixups

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkcollections
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp
import math
import numpy as np
import sirepo.sim_data
from sirepo.template import srw_common

_SIM_DATA, SIM_TYPE, _SCHEMA = sirepo.sim_data.template_globals('srw')

def do(template, data):
    _do_beamline(template, data)
    dm = data.models
    hv = ('horizontalPosition', 'horizontalRange', 'verticalPosition', 'verticalRange')
    if 'samplingMethod' not in dm.simulation:
        simulation = dm.simulation
        simulation.samplingMethod = 1 if simulation.sampleFactor > 0 else 2
        for k in hv:
            simulation[k] = dm.initialIntensityReport[k]
    if 'horizontalPosition' in dm.initialIntensityReport:
        for k in dm:
            if k == 'sourceIntensityReport' or k == 'initialIntensityReport' or _SIM_DATA.is_watchpoint(k):
                for f in hv:
                    del dm[k][f]
    if 'indexFile' in data.models.tabulatedUndulator:
        del data.models.tabulatedUndulator['indexFile']
    data = _do_electron_beam(template, data)
    for c in 'horizontal', 'vertical':
        n = '{}DeflectingParameter'.format(c)
        if n not in dm.undulator:
            u = dm.undulator
            u[n] = template.process_undulator_definition(
                pkcollections.Dict(
                    undulator_definition='B',
                    undulator_parameter=None,
                    amplitude=float(u['{}Amplitude'.format(c)]),
                    undulator_period=float(u.period) / 1000.0
                ),
            ).undulator_parameter
    u = dm.undulator
    if 'effectiveDeflectingParameter' not in u and 'horizontalDeflectingParameter' in u:
        u.effectiveDeflectingParameter = math.sqrt(
            u.horizontalDeflectingParameter ** 2 + u.verticalDeflectingParameter ** 2,
        )
    for k in (
        'photonEnergy',
        'horizontalPointCount',
        'horizontalPosition',
        'horizontalRange',
        'sampleFactor',
        'samplingMethod',
        'verticalPointCount',
        'verticalPosition',
        'verticalRange',
    ):
        if k not in dm.sourceIntensityReport:
            dm.sourceIntensityReport[k] = dm.simulation[k]
    if 'photonEnergy' not in dm.gaussianBeam:
        dm.gaussianBeam.photonEnergy = dm.simulation.photonEnergy
    if 'length' in dm.tabulatedUndulator:
        tabulated_undulator = dm.tabulatedUndulator
        und_length = template.compute_undulator_length(tabulated_undulator)
        if _SIM_DATA.srw_uses_tabulated_zipfile(data) and 'length' in und_length:
            dm.undulator.length = und_length.length
        del dm.tabulatedUndulator['length']
    if 'longitudinalPosition' in dm.tabulatedUndulator:
        u = dm.tabulatedUndulator
        for k in (
            'undulatorParameter',
            'period',
            'length',
            'longitudinalPosition',
            'horizontalAmplitude',
            'horizontalSymmetry',
            'horizontalInitialPhase',
            'verticalAmplitude',
            'verticalSymmetry',
            'verticalInitialPhase',
        ):
            if k in u:
                if _SIM_DATA.srw_is_tabulated_undulator_source(dm.simulation):
                    dm.undulator[k] = u[k]
                del u[k]
    if 'name' not in dm['tabulatedUndulator']:
        u = dm.tabulatedUndulator
        u.name = u.undulatorSelector = 'Undulator'
    if dm.tabulatedUndulator.get('id', '1') == '1':
        dm.tabulatedUndulator.id = '{} 1'.format(dm.simulation.simulationId)
    if len(dm.postPropagation) == 9:
        dm.postPropagation += [0, 0, 0, 0, 0, 0, 0, 0]
        for i in dm.propagation:
            for r in dm.propagation[i]:
                r += [0, 0, 0, 0, 0, 0, 0, 0]
    if 'electronBeams' in dm:
        del dm['electronBeams']
    return data


def _do_beamline(template, data):
    dm = data.models
    for i in dm.beamline:
        t = i.type
        if t == 'ellipsoidMirror':
            if 'firstFocusLength' not in i:
                i.firstFocusLength = i.position
        if t in ('grating', 'ellipsoidMirror', 'sphericalMirror', 'toroidalMirror'):
            if 'grazingAngle' not in i:
                angle = 0
                if item.normalVectorX:
                    angle = math.acos(abs(float(i.normalVectorX))) * 1000
                elif i.normalVectorY:
                    angle = math.acos(abs(float(i.normalVectorY))) * 1000
                i.grazingAngle = angle
        if 'grazingAngle' in i and 'normalVectorX' in i and 'autocomputeVectors' not in i:
            i.autocomputeVectors = '1'
        if t == 'crl':
            for k, v in pkcollections.Dict(
                material='User-defined',
                method='server',
                absoluteFocusPosition=None,
                focalDistance=None,
                tipRadius=float(i.radius) * 1e6,  # m -> um
                tipWallThickness=float(i.wallThickness) * 1e6,  # m -> um
            ).items():
                if k not in i:
                    i[k] = v
            if not i.focalDistance:
                template.compute_crl_focus(i)
        if t == 'crystal':
            if 'diffractionAngle' not in i:
                allowed_angles = [x[0] for x in _SCHEMA.enum.DiffractionPlaneAngle]
                i.diffractionAngle = _find_closest_angle(i.grazingAngle or 0, allowed_angles)
                if i.tvx == '':
                    i.tvx = i.tvy = 0
                _SIM_DATA.srw_compute_crystal_grazing_angle(i)
        if t == 'sample':
            if 'horizontalCenterCoordinate' not in i:
                i.horizontalCenterCoordinate = _SCHEMA.model.sample.horizontalCenterCoordinate[2]
                i.verticalCenterCoordinate = _SCHEMA.model.sample.verticalCenterCoordinate[2]
            if 'cropArea' not in i:
                for f in (
                    'areaXEnd',
                    'areaXStart',
                    'areaYEnd',
                    'areaYStart',
                    'backgroundColor',
                    'cropArea',
                    'cutoffBackgroundNoise',
                    'invert',
                    'outputImageFormat',
                    'rotateAngle',
                    'rotateReshape',
                    'shiftX',
                    'shiftY',
                    'tileColumns',
                    'tileImage',
                    'tileRows',
                ):
                    i[f] = _SCHEMA.model.sample[f][2]
            if 'transmissionImage' not in i:
                i.transmissionImage = _SCHEMA.model.sample.transmissionImage[2]
        if t in ('crl', 'grating', 'ellipsoidMirror', 'sphericalMirror') \
            and 'horizontalOffset' not in i:
            i.horizontalOffset = 0
            i.verticalOffset = 0
        if 'autocomputeVectors' in i:
            if i.autocomputeVectors == '0':
                i.autocomputeVectors = 'none'
            elif i.autocomputeVectors == '1':
                i.autocomputeVectors = 'vertical' if i.normalVectorX == 0 else 'horizontal'
        _SIM_DATA.update_model_defaults(i, t)
        if t in {'crystal'}:
            template._compute_crystal_orientation(i)
        if t in {'grating'}:
            i.energyAvg = dm.simulation.photonEnergy
            template._compute_PGM_value(i)

def _do_electron_beam(template, data):
    dm = data.models
    if 'beamDefinition' not in dm['electronBeam']:
        srw_common.process_beam_parameters(dm['electronBeam'])
        dm['electronBeamPosition']['drift'] = template.calculate_beam_drift(
            dm['electronBeamPosition'],
            dm['simulation']['sourceType'],
            dm['tabulatedUndulator']['undulatorType'],
            float(dm['undulator']['length']),
            float(dm['undulator']['period']) / 1000.0,
        )
    return data


def _find_closest_angle(angle, allowed_angles):
    """Find closest string value from the input list to
       the specified angle (in radians).
    """
    def _wrap(a):
        """Convert an angle to constraint it between -pi and pi.
           See https://stackoverflow.com/a/29237626/4143531 for details.
        """
        return np.arctan2(np.sin(a), np.cos(a))

    angles = np.array([float(x) for x in allowed_angles])
    threshold = np.min(np.diff(angles))
    return allowed_angles[
        np.where(np.abs(_wrap(angle) - angles) < threshold / 2.0)[0][0]
    ]
