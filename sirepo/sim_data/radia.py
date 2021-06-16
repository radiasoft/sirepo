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
            'reset',
            #'solver', 'reset'
        ):
            return 'animation'
        if analysis_model in (
            'solverAnimation',
        ):
            return 'solverAnimation'
        return super(SimData, cls)._compute_model(analysis_model, *args, **kwargs)

    @classmethod
    def __dynamic_defaults(cls, data, model):
        """defaults that depend on the current data"""
        return PKDict()

    @classmethod
    def fixup_old_data(cls, data):

        def _find_obj_by_name(obj_arr, obj_name):
            return next((x for x in obj_arr if x.name == obj_name), None)

        dm = data.models
        cls._init_models(
            dm,
            None,
            dynamic=lambda m: cls.__dynamic_defaults(data, m)
        )
        if not dm.fieldPaths.get('paths'):
            dm.fieldPaths.paths = []
        if dm.simulation.get('isExample'):
            if not dm.simulation.get('exampleName'):
                dm.simulation.exampleName = dm.simulation.name
            if dm.simulation.name == 'Wiggler':
                dm.geometry.isSolvable = '0'
        if dm.simulation.magnetType == 'undulator':
            if not dm.hybridUndulator.get('magnetBaseObjectId'):
                dm.hybridUndulator.magnetBaseObjectId = _find_obj_by_name(dm.geometry.objects, 'Magnet Block').id
            if not dm.hybridUndulator.get('poleBaseObjectId'):
                dm.hybridUndulator.poleBaseObjectId = _find_obj_by_name(dm.geometry.objects, 'Pole').id
            if not dm.simulation.get('heightAxis'):
                dm.simulation.heightAxis = 'z'
        for o in dm.geometry.objects:
            if not o.get('bevels'):
                o.bevels = []
        sch = cls.schema()
        for m in [m for m in dm if m in sch.model]:
            s_m = sch.model[m]
            for f in [
                f for f in s_m if f in dm[m] and s_m[f][1] == 'Boolean' and
                    not dm[m][f]
            ]:
                dm[m][f] = '0'
        cls._organize_example(data)

    @classmethod
    def _lib_file_basenames(cls, data):
        res = []
        if 'dmpImportFile' in data.models.simulation:
            res.append(f'{cls.schema().constants.radiaDmpFileType}.{data.models.simulation.dmpImportFile}')
        if 'fieldType' in data:
            res.append(cls.lib_file_name_with_model_field(
                'fieldPath',
                data.fieldType,
                data.name + '.' + data.fileType))
        return res
