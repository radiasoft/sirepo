# -*- coding: utf-8 -*-
u"""synergia simulation data operations

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
import sirepo.sim_data

class SimData(sirepo.sim_data.SimDataBase):

    @classmethod
    def fixup_old_data(cls, data):
        dm = data.models
        cls._init_models(
            dm,
            (
                'beamEvolutionAnimation',
                'bunch',
                'bunchAnimation',
                'bunchTwiss',
                'simulationSettings',
                'turnComparisonAnimation',
                'twissReport',
                'twissReport2',
            ),
        )
        if 'bunchReport' in dm:
            del dm['bunchReport']
            for i in range(1, 5):
                m = dm['bunchReport{}'.format(i)] = PKDict()
                cls.update_model_defaults(m, 'bunchReport')
                if i == 1:
                    m.y = 'xp'
                elif i == 2:
                    m.x = 'y'
                    m.y = 'yp'
                elif i == 4:
                    m.x = 'z'
                    m.y = 'zp'
        cls._organize_example(data)

    @classmethod
    def _compute_model(cls, analysis_model, *args, **kwargs):
        if 'bunchReport' in analysis_model:
            return 'bunchReport'
        # twissReport2 and twissReport are compute_models
        return super(SimData, cls)._compute_model(analysis_model, *args, **kwargs)

    @classmethod
    def _compute_job_fields(cls, data, r, compute_model):
        res = ['beamlines', 'elements']
        if 'bunchReport' in r:
            res += ['bunch', 'simulation.visualizationBeamlineId']
        elif r == 'twissReport':
            res += ['simulation.activeBeamlineId']
        elif 'twissReport' in r:
            res += ['simulation.visualizationBeamlineId']
        return res

    @classmethod
    def _lib_files(cls, data):
        res = []
        b = data.models.bunch
        if b.distribution == 'file':
            res.append(cls.lib_file_name('bunch', 'particleFile', b.particleFile))
        return res
