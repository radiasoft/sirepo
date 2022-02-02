# -*- coding: utf-8 -*-
u"""simulation data operations

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkdebug import pkdp
import sirepo.sim_data


class SimData(sirepo.sim_data.SimDataBase):
    pass

    @classmethod
    def fixup_old_data(cls, data):
        pass

    @classmethod
    def _compute_job_fields(cls, data, r, compute_model):
        return []

    @classmethod
    def _compute_model(cls, analysis_model, resp):
        return analysis_model

    @classmethod
    def _lib_file_basenames(cls, data):
        def _input_files():
            for k, v in data.models.inputFiles.items():
                if v:
                    yield cls.lib_file_name_with_model_field('inputFiles', k, v)
        return [
            data.models.scans.catalogName + '.zip',
        ] + list(_input_files())
