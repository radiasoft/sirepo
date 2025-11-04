# -*- coding: utf-8 -*-
"""elegant simulation data functions

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
from sirepo.template.lattice import LatticeUtil
import sirepo.sim_data.lattice


class SimData(sirepo.sim_data.lattice.LatticeSimData):
    _BUNCH_REPORT_DEPENDENCIES = ["bunch", "bunchSource", "bunchFile", "rpnVariables"]

    @classmethod
    def fixup_old_data(cls, data, qcall, **kwargs):
        super().fixup_old_data(data, qcall, **kwargs)
        dm = data.models
        cls._init_models(
            dm, ("bunch", "bunchFile", "bunchSource", "simulation", "twissReport")
        )
        for m in dm.elements:
            if m.type == "WATCH":
                m.filename = "1"
                if m.mode == "coordinates" or m.mode == "coord":
                    m.mode = "coordinate"
        cls._organize_example(data)
        from sirepo.template.elegant import OutputFileIterator

        LatticeUtil.fixup_output_files(data, cls.schema(), OutputFileIterator(True))

    @classmethod
    def _compute_job_fields(cls, data, report, compute_model):
        res = super()._compute_job_fields(data, report, compute_model)
        if compute_model == "twissReport":
            res += cls._BUNCH_REPORT_DEPENDENCIES + [
                "elements",
                "beamlines",
                "commands",
                "simulation.activeBeamlineId",
            ]
        return res

    @classmethod
    def _lib_file_basenames(cls, data):
        res = super()._lib_file_basenames(data)
        if data.models.bunchFile.sourceFile:
            res.append(
                cls.lib_file_name_with_model_field(
                    "bunchFile", "sourceFile", data.models.bunchFile.sourceFile
                )
            )
        return res
