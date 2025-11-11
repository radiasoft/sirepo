# -*- coding: utf-8 -*-
"""simulation data operations

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkdebug import pkdc, pkdlog, pkdp
import sirepo.sim_data.lattice


class SimData(sirepo.sim_data.lattice.LatticeSimData):
    _BUNCH_REPORT_DEPENDENCIES = [
        "bunch",
        "commands",
        "rpnVariables",
        "simulation.visualizationBeamlineId",
    ]

    @classmethod
    def fixup_old_data(cls, data, qcall, **kwargs):
        super().fixup_old_data(data, qcall, **kwargs)
        cls._init_models(
            data.models,
            (
                "bunch",
                "simulation",
                "twissReport",
            ),
        )

    @classmethod
    def _compute_job_fields(cls, data, report, compute_model):
        res = super()._compute_job_fields(data, report, compute_model)
        if report == "twissReport":
            res += [
                "beamlines",
                "elements",
                "simulation.activeBeamlineId",
                "rpnVariables",
            ]
        return res

    @classmethod
    def _lib_file_basenames(cls, data):
        res = super()._lib_file_basenames(data)
        if data.models.bunch.beamDefinition == "file" and data.models.bunch.sourceFile:
            res += [
                cls.lib_file_name_with_model_field(
                    "bunch", "sourceFile", data.models.bunch.sourceFile
                ),
            ]
        return res
