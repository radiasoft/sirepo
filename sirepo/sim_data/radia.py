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
    def _compute_job_fields(cls, data, r, compute_model):
        res = cls._non_analysis_fields(data, r) + []
        return res

    @classmethod
    def _compute_model(cls, analysis_model, *args, **kwargs):
        if analysis_model in (
            'solver', 'reset'
        ):
            return 'animation'
        return super(SimData, cls)._compute_model(analysis_model, *args, **kwargs)

    @classmethod
    def _is_parallel(cls, analysis_model):
        return False
        #m = analysis_model.report if isinstance(analysis_model, dict) else analysis_model
        #is_p = m in (
        #    'kickMap',
        #)
        #pkdp(f'CHECK IS_P FOR {m}: {is_p}')
        #return is_p

    @classmethod
    def __dynamic_defaults(cls, data, model):
        """defaults that depend on the current data"""
        return PKDict()

    @classmethod
    def fixup_old_data(cls, data):
        dm = data.models
        cls._init_models(
            dm,
            None,
            dynamic=lambda m: cls.__dynamic_defaults(data, m)
        )
        if not dm.fieldPaths.get('paths', []):
            dm.fieldPaths.paths = []
        if dm.simulation.get('isExample') and dm.simulation.name == 'Wiggler':
            dm.geometry.isSolvable = '0'
        cls._organize_example(data)

    @classmethod
    def _lib_file_basenames(cls, data):
        res = []
        if 'fieldType' in data:
            res.append(cls.lib_file_name_with_model_field(
                'fieldPath',
                data.fieldType,
                data.name + '.' + data.fileType))
        return res
