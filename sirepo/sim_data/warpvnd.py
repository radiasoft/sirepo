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
        dm.setdefault(optimizer=PKDict()).setdefault(
            constraints=[],
            enabledFields=PKDict(),
            fields=[],
        )
        cls.init_models(
            dm,
            (
                'anode',
                'egunCurrentAnimation',
                'impactDensityAnimation',
                'optimizer',
                'optimizerAnimation',
                'optimizerStatus',
                'particle3d',
                'particleAnimation',
                'simulation',
                'simulationGrid',
                'fieldCalcAnimation',
                'fieldCalculationAnimation',
                'fieldComparisonAnimation',
                'fieldComparisonReport',
                'simulation',
            ),
            dynamic=lambda m: cls._dynamic_defaults(data, m),
        )
        pkcollections.unchecked_del(dm.particle3d, 'joinEvery')
#TODO(robnagler) is this a denormalization of conductors?
        s = cls.schema()
        for c in dm.get('conductorTypes', []):
#TODO(robnagler) can a conductor type be none?
            if c is None:
                continue
#TODO(robnagler) why is this not a bool?
            x = c.setdefault(isConductor='1' if c.voltage > 0 else '0')
            c.setdefault(
                color=s.get('zeroVoltsColor' if x == '0' else 'nonZeroVoltsColor'),
            )
#TODO(robnagler) how does this work? bc names are on schema, not conductor
            cls.update_model_defaults(c, c.get('type', 'box'))
        for c in dm.conductors:
            cls.update_model_defaults(c, 'conductorPosition')
        cls.organize_example(data)

    @classmethod
    def is_3d(cls, data):
        return data.models.simulationGrid.simulation_mode == '3d'

    @classmethod
    def _dynamic_defaults(cls, data, model):
        """defaults that depend on the current data"""
        if not model.startswith('fieldComparison'):
            return PKDict()
        g = data.models.simulationGrid
        t = cls.is_3d(data)
        return PKDict(
            dimension='x',
            xCell1=0,
            xCell2=int(g.num_x / 2.),
            xCell3=g.num_x,
            yCell1=0,
            yCell2=int(g.num_y / 2.) if t else 0,
            yCell3=g.num_y if t else 0,
            zCell1=0,
            zCell2=int(g.num_z / 2.),
            zCell3=g.num_z,
        )
