# -*- coding: utf-8 -*-
u"""simulation data operations

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
        cls.init_models(
            dm,
            (
                'SPNTRK',
                'SRLOSS',
                'bunch',
                'bunchAnimation',
                'bunchAnimation2',
                'elementStepAnimation',
                'energyAnimation',
                'opticsReport',
                'particle',
                'particleAnimation',
                'particleCoordinate',
                'simulationSettings',
                'tunesReport',
                'twissReport',
                'twissReport2',
                'twissSummaryReport',
            ),
        )
        if 'coordinates' not in dm.bunch:
            b = dm.bunch
            b.coordinates = []
            for _ in range(b.particleCount2):
                c = PKDict()
                cls.update_model_defaults(c, 'particleCoordinate')
                b.coordinates.append(c)
        # move spntrk from simulationSettings (older) or bunch if present
        for m in 'simulationSettings', 'bunch':
            if 'spntrk' in dm:
                data.models.SPNTRK.KSO = dm[m].spntrk
                del dm[m]['spntrk']
                for f in 'S_X', 'S_Y', 'S_Z':
                    if f in dm[m]:
                        df.SPNTRK[f] = dm[m][f]
                        del dm[m][f]
        for e in dm.elements:
            cls.update_model_defaults(e, e.type)
        cls.organize_example(data)
