# -*- coding: utf-8 -*-
u"""simulation data operations

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkcollections
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
from pykern.pkdebug import pkdp
import re
import sirepo.sim_data


class SimData(sirepo.sim_data.SimDataBase):

    ANALYSIS_ONLY_FIELDS = frozenset(('colorMap', 'notes', 'color', 'impactColorMap', 'axes', 'slice'))

    @classmethod
    def _compute_model(cls, analysis_model, *args, **kwargs):
        if analysis_model == 'optimizerAnimation':
            return analysis_model
        if analysis_model in (
            'fieldCalcAnimation',
            'fieldCalculationAnimation',
            'fieldComparisonAnimation',
        ):
            return 'fieldCalculationAnimation'
        #TODO(pjm): special case, should be an Animation model
        if analysis_model == 'particle3d':
            return 'animation'
        return super(SimData, cls)._compute_model(analysis_model, *args, **kwargs)

    @classmethod
    def fixup_old_data(cls, data):
        dm = data.models
        dm.pksetdefault(optimizer=PKDict())
        dm.optimizer.setdefault(
            constraints=[],
            enabledFields=PKDict(),
            fields=[],
        )
        cls._init_models(
            dm,
            (
                # simulationGrid must be first
                'simulationGrid',
                'anode',
                'egunCurrentAnimation',
                'fieldAnimation',
                'fieldCalcAnimation',
                'fieldCalculationAnimation',
                'fieldComparisonAnimation',
                'fieldComparisonReport',
                'fieldReport',
                'impactDensityAnimation',
                'optimizer',
                'optimizerAnimation',
                'optimizerStatus',
                'particle3d',
                'particleAnimation',
                'simulation',
            ),
            dynamic=lambda m: cls.__dynamic_defaults(data, m),
        )
        pkcollections.unchecked_del(dm.particle3d, 'joinEvery')
#TODO(robnagler) is this a denormalization of conductors?
        s = cls.schema()
        for c in dm.get('conductorTypes', []):
#TODO(robnagler) can a conductor type be none?
            if c is None:
                continue
#TODO(robnagler) why is this not a bool?
            x = c.setdefault('isConductor', '1' if c.voltage > 0 else '0')
            c.setdefault(
                color=s.get('zeroVoltsColor' if x == '0' else 'nonZeroVoltsColor'),
            )
#TODO(robnagler) how does this work? bc names are on schema, not conductor
            cls.update_model_defaults(c, c.get('type', 'box'))
        for c in dm.conductors:
            cls.update_model_defaults(c, 'conductorPosition')
        cls._organize_example(data)

    @classmethod
    def warpvnd_is_3d(cls, data):
        return data.models.simulationGrid.simulation_mode == '3d'

    @classmethod
    def _compute_job_fields(cls, data, r, compute_model):
        res = ['simulationGrid']
        res.append(cls.__non_opt_fields_to_array(data.models.beam))
        for container in ('conductors', 'conductorTypes'):
            for m in data.models[container]:
                res.append(cls.__non_opt_fields_to_array(m))
        return res + cls._non_analysis_fields(data, r)

    @classmethod
    def __dynamic_defaults(cls, data, model):
        """defaults that depend on the current data"""
        if not model.startswith('fieldComparison'):
            return PKDict()
        g = data.models.simulationGrid
        t = cls.warpvnd_is_3d(data)
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

    @classmethod
    def _lib_files(cls, data):
        res = []
        for m in data.models.conductorTypes:
            if m.type == 'stl':
                res.append(cls.lib_file_name('stl', 'file', m.file))
        return res

    @classmethod
    def __non_opt_fields_to_array(cls, model):
        res = []
        for f in model:
            if not re.search(r'\_opt$', f) and f not in cls.ANALYSIS_ONLY_FIELDS:
                res.append(model[f])
        return res
