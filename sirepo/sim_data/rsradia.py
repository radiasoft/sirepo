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
    GEOM_FILE = 'geom.h5'

    @classmethod
    def _compute_job_fields(cls, data, r, compute_model):
        res = cls._non_analysis_fields(data, r) + []
        return res

    @classmethod
    def _compute_model(cls, analysis_model, *args, **kwargs):
        #pkdp('_compute_model {}', analysis_model)
        if analysis_model in (
            'solver',
        ):
            return 'animation'
        return super(SimData, cls)._compute_model(analysis_model, *args, **kwargs)

    @classmethod
    def fixup_old_data(cls, data):
        cls._init_models(data.models)
        cls._organize_example(data)

    #@classmethod
    #def _compute_job_fields(cls, data, *args, **kwargs):
    #    return [
    #        data.report,
    #    ]

    @classmethod
    def _lib_file_basenames(cls, data):
        return []
