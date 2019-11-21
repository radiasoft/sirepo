# -*- coding: utf-8 -*-
u"""simulation data operations

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkcollections
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
import sirepo.sim_data


class SimData(sirepo.sim_data.SimDataBase):

    ANALYSIS_ONLY_FIELDS = frozenset(('colorMap', 'notes'))

    @classmethod
    def fixup_old_data(cls, data):
        dm = data.models
        dm.setdefault(
            laserPreviewReport=PKDict(),
            particleAnimation=PKDict(
                x='z',
                y='x',
                histogramBins=100,
            ),
        )
        dm.particleAnimation.setdefault(
            histogramBins=100,
            framesPerSecond=20,
        )
        dm.fieldAnimation.setdefault(framesPerSecond=20)
        #TODO(robnagler) was conditional only on rScale, so is this right?
        dm.simulationGrid.setdefault(
            rScale=4,
            rLength='20.324980154380',
            rMin=0,
            rMax='20.324980154380',
            rCellsPerSpotSize=8,
            rCount=32,
            zScale=2,
            zLength='20.324980154631',
            zMin='-20.324980154631',
            zMax='1.60',
            zCellsPerWavelength=8,
            zCount=214,
            rParticlesPerCell=1,
            zParticlesPerCell=2,
            rCellResolution=40,
            zCellResolution=40,
        )
        pkcollections.unchecked_del(
            dm.simulationGrid,
            'xMin',
            'xMax',
            'xCount',
            'zLambda',
        )
        #TODO(robnagler) is this ok was conditional on field, only
        dm.laserPreviewReport.setdefault(
            field='E',
            coordinate='y',
            mode='1',
        )
        dm.simulation.setdefault(
            sourceType='laserPulse',
            folder='/',
        )
        dm.setdefault(
            'electronBeam',
            PKDict(charge=1.0e-08, energy=23),
        )
        if 'rmsRadius' in dm.electronBeam and dm.electronBeam.rmsRadius == 0:
            del dm.electronBeam['rmsRadius']
        dm.electronBeam.setdefault(
            rmsLength=0,
            bunchLength=0,
            beamRadiusMethod='a',
            transverseEmittance=0.00001,
            rmsRadius=15,
            beamBunchLengthMethod='s',
        )
        dm.setdefault(
            'beamPreviewReport',
            PKDict(
                x='z',
                y='x',
                histogramBins=100,
            )
        )
        dm.setdefault('beamAnimation', dm.particleAnimation.copy())
        if 'xMin' not in dm.particleAnimation:
            for v in 'x', 'y', 'z':
                dm.particleAnimation.update({
                    '{}Min'.format(v): 0,
                    '{}Max'.format(v): 0,
                    'u{}Min'.format(v): 0,
                    'u{}Max'.format(v): 0,
                })
        for m in 'beamAnimation', 'fieldAnimation', 'particleAnimation':
            cls.update_model_defaults(dm[m], m)
        cls._organize_example(data)



    @classmethod
    def _compute_job_fields(cls, data, r, compute_model):
        if r not in ('beamPreviewReport', 'laserPreviewReport'):
            return []
        return cls._non_analysis_fields(data, r) + [
            'simulation.sourceType',
            'electronBeam',
            'electronPlasma',
            'laserPulse',
            'simulationGrid',
        ]


    @classmethod
    def _lib_file_basenames(cls, data):
        return []
