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
    def does_api_reply_with_file(cls, api, method):
        return api in "api_statelessCompute" and method == "download_analysis_pdfs"

    @classmethod
    def fixup_old_data(cls, data, qcall, **kwargs):
        cls._init_models(data.models)
        # always clear confirmation for next session
        data.models.runAnalysis.confirmRunAnalysis = "0"
        if data.models.simulation.folder == "/Examples":
            data.models.simulation.folder = "/"

    @classmethod
    def _compute_job_fields(cls, data, r, compute_model):
        return []

    @classmethod
    def _compute_model(cls, analysis_model, resp):
        return analysis_model

    @classmethod
    def _lib_file_basenames(cls, data):
        return []
