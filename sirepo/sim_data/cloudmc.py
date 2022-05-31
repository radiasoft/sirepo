# -*- coding: utf-8 -*-
u"""simulation data operations

:copyright: Copyright (c) 202 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkdebug import pkdc, pkdlog, pkdp
import sirepo.sim_data


class SimData(sirepo.sim_data.SimDataBase):

    @classmethod
    def dagmc_filename(cls, data):
        return cls.lib_file_name_with_model_field(
            'geometryInput',
            'dagmcFile',
            data.models.geometryInput.dagmcFile,
        )

    @classmethod
    def fixup_old_data(cls, data):
        dm = data.models
        cls._init_models(dm)

    @classmethod
    def _compute_job_fields(cls, data, *args, **kwargs):
        return []

    @classmethod
    def _compute_model(cls, analysis_model, *args, **kwargs):
        return analysis_model;

    @classmethod
    def _lib_file_basenames(cls, data):
        return [
            cls.dagmc_filename(data),
        ]
