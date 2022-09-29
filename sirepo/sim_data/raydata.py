# -*- coding: utf-8 -*-
"""simulation data operations

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkdebug import pkdp
import re
import sirepo.sim_data


class SimData(sirepo.sim_data.SimDataBase):
    @classmethod
    def fixup_old_data(cls, data):
        cls._init_models(data.models)

    @classmethod
    def _compute_job_fields(cls, data, r, compute_model):
        return []

    @classmethod
    def _compute_model(cls, analysis_model, resp):
        return analysis_model

    @classmethod
    def _lib_file_basenames(cls, data):
        return []
