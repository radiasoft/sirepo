# -*- coding: utf-8 -*-
"""simulation data operations

:copyright: Copyright (c) 2024 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
import sirepo.sim_data


class SimData(sirepo.sim_data.SimDataBase):
    @classmethod
    def fixup_old_data(cls, data, qcall, **kwargs):
        dm = data.models
        cls._init_models(
            dm,
            [
                "bunchAnimation",
                "bunchAnimation1",
                "bunchAnimation2",
                "bunchAnimation3",
                "distribution",
                "sigmaAnimation",
                "simulationSettings",
                "twissAnimation",
            ],
        )
        if "bunchReport1" not in dm:
            for i in range(1, 5):
                m = dm[f"bunchReport{i}"] = PKDict()
                cls.update_model_defaults(m, "bunchReport")

    @classmethod
    def _compute_model(cls, analysis_model, *args, **kwargs):
        if "bunchReport" in analysis_model:
            return "bunchReport"
        return super(SimData, cls)._compute_model(analysis_model, *args, **kwargs)

    @classmethod
    def _compute_job_fields(cls, data, r, compute_model):
        if "bunchReport" in r:
            return ["distribution", "rpnVariables"]
        return []

    @classmethod
    def _lib_file_basenames(cls, data):
        res = []
        d = data.models.distribution
        if d.distributionType == "File" and d.distributionFile:
            res.append(
                cls.lib_file_name_with_model_field(
                    "distribution", "distributionFile", d.distributionFile
                )
            )
        return res
