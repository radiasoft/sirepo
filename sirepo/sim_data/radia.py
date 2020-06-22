# -*- coding: utf-8 -*-
u"""simulation data operations

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkdebug import pkdc, pkdlog, pkdp
import sirepo.sim_data


class SimData(sirepo.sim_data.SimDataBase):
    ANALYSIS_ONLY_FIELDS = frozenset(('colorMap', 'name', 'notes', 'scaling'))

    @classmethod
    def _compute_job_fields(cls, data, r, compute_model):
        #res = cls._non_analysis_fields(data, r) + []
        res = []
        return res

    @classmethod
    def _compute_model(cls, analysis_model, *args, **kwargs):
        # funnel everything into geometry so they all use the same run_dir
        if analysis_model in ('geometry', 'reset', 'solver',):
            return 'geometry'
        return super(SimData, cls)._compute_model(analysis_model, *args, **kwargs)

    @classmethod
    def fixup_old_data(cls, data):
        cls._init_models(data.models)
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
