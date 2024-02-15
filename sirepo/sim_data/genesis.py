# -*- coding: utf-8 -*-
"""simulation data operations

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkdebug import pkdc, pkdlog, pkdp
import sirepo.sim_data


class SimData(sirepo.sim_data.SimDataBase):
    @classmethod
    def fixup_old_data(cls, data, qcall, **kwargs):
        dm = data.models
        cls._init_models(dm)

    @classmethod
    def _lib_file_basenames(cls, data):
        res = []
        io = data.models.io
        for f in (
            "beamfile",
            "maginfile",
            "radfile",
            "partfile",
            "fieldfile",
            "distfile",
        ):
            if io[f]:
                res.append(cls.lib_file_name_with_model_field("io", f, io[f]))
        return res

    @classmethod
    def _compute_job_fields(cls, data, r, compute_model):
        return []
