# -*- coding: utf-8 -*-
"""simulation data operations
:copyright: Copyright (c) 2024 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkdebug import pkdc, pkdlog, pkdp
import sirepo.sim_data.lattice


class SimData(sirepo.sim_data.lattice.LatticeSimData):
    _BUNCH_REPORT_DEPENDENCIES = ["distribution", "rpnVariables"]

    @classmethod
    def fixup_old_data(cls, data, qcall, **kwargs):
        super().fixup_old_data(data, qcall, **kwargs)
        dm = data.models
        cls._init_models(
            dm,
            [
                "distribution",
                "simulationSettings",
                "statAnimation",
            ],
        )

    @classmethod
    def _lib_file_basenames(cls, data):
        res = super()._lib_file_basenames(data)
        d = data.models.distribution
        if d.distributionType == "File" and d.distributionFile:
            res.append(
                cls.lib_file_name_with_model_field(
                    "distribution", "distributionFile", d.distributionFile
                )
            )
        return res
