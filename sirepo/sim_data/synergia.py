# -*- coding: utf-8 -*-
u"""synergia simulation data operations

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkcollections
from pykern.pkdebug import pkdp
from sirepo import simulation_db
import sirepo.sim_data


class SimData(sirepo.sim_data.SimDataBase):

    @classmethod
    def fixup_old_data(cls, data):
        dm = data.models
        for m in [
            'beamEvolutionAnimation',
            'bunch',
            'bunchAnimation',
            'bunchTwiss',
            'simulationSettings',
            'turnComparisonAnimation',
            'twissReport',
            'twissReport2',
        ]:
            if m not in dm:
                dm[m] = {}
            cls.update_model_defaults(dm[m], m)
        if 'bunchReport' in dm:
            del dm['bunchReport']
            for i in range(4):
                m = 'bunchReport{}'.format(i + 1)
                model = dm[m] = {}
                cls.update_model_defaults(dm[m], 'bunchReport')
                if i == 0:
                    model['y'] = 'xp'
                elif i == 1:
                    model['x'] = 'y'
                    model['y'] = 'yp'
                elif i == 3:
                    model['x'] = 'z'
                    model['y'] = 'zp'
        cls.organize_example(data)
