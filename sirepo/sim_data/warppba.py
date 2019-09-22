# -*- coding: utf-8 -*-
u"""simulation data operations

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
from pykern import pkcollections
from pykern.pkdebug import pkdp
from sirepo import simulation_db
import sirepo.sim_data


class SimData(sirepo.sim_data.SimDataBase):

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
            simulationStatus=PKDict(),
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
        dm.simulation.setdefault(sourceType='laserPulse')
        if 'electronBeam' not in dm:
            dm['electronBeam'] = {
                'charge': 1.0e-08,
                'energy': 23,
            }
        if 'beamPreviewReport' not in dm:
            dm['beamPreviewReport'] = {
                'x': 'z',
                'y': 'x',
                'histogramBins': 100
            }
        if 'beamAnimation' not in dm:
            dm['beamAnimation'] = dm['particleAnimation'].copy()
        if 'rCellResolution' not in dm['simulationGrid']:
            grid = dm['simulationGrid']
            grid['rCellResolution'] = 40
            grid['zCellResolution'] = 40
        if 'rmsLength' not in dm['electronBeam']:
            beam = dm['electronBeam']
            beam['rmsLength'] = 0
            beam['rmsRadius'] = 0
            beam['bunchLength'] = 0
            beam['transverseEmittance'] = 0
        if 'xMin' not in dm['particleAnimation']:
            animation = dm['particleAnimation']
            for v in ('x', 'y', 'z'):
                animation['{}Min'.format(v)] = 0
                animation['{}Max'.format(v)] = 0
                animation['u{}Min'.format(v)] = 0
                animation['u{}Max'.format(v)] = 0
        if 'beamRadiusMethod' not in dm['electronBeam']:
            beam = dm['electronBeam']
            beam['beamRadiusMethod'] = 'a'
            beam['transverseEmittance'] = 0.00001
            beam['rmsRadius'] = 15
            beam['beamBunchLengthMethod'] = 's'
        if 'folder' not in dm['simulation']:
            dm['simulation']['folder'] = '/'
        for m in ('beamAnimation', 'fieldAnimation', 'particleAnimation'):
            cls.update_model_defaults(dm[m], m)
        cls.organize_example(data)
