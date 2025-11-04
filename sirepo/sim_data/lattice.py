# -*- coding: utf-8 -*-
"""Common simulation data operations for lattice apps
:copyright: Copyright (c) 2025 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
import sirepo.sim_data
import sirepo.template.lattice


class LatticeSimData(sirepo.sim_data.SimDataBase):

    @classmethod
    def fixup_old_data(cls, data, qcall, **kwargs):
        dm = data.models
        dm.setdefault("rpnVariables", [])
        for i in range(1, 5):
            n = f"bunchReport{i}"
            dm.setdefault(n, PKDict())
            cls.update_model_defaults(dm[n], "bunchReport")
        for c in ("commands", "elements"):
            for m in dm.get(c, []):
                cls.update_model_defaults(
                    m, sirepo.template.lattice.LatticeUtil.model_name_for_data(m)
                )

    @classmethod
    def _compute_job_fields(cls, data, report, compute_model):
        if compute_model == "bunchReport":
            return cls._BUNCH_REPORT_DEPENDENCIES
        return [report]

    @classmethod
    def _compute_model(cls, analysis_model, *args, **kwargs):
        if "bunchReport" in analysis_model:
            return "bunchReport"
        return super()._compute_model(analysis_model, *args, **kwargs)

    @classmethod
    def _lib_file_basenames(cls, data):
        return (
            sirepo.template.lattice.LatticeUtil(data, cls.schema())
            .iterate_models(sirepo.template.lattice.InputFileIterator(cls))
            .result
        )
