# -*- coding: utf-8 -*-
"""SILAS simulation data operations

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
import sirepo.sim_data


class SimData(sirepo.sim_data.SimDataBase):
    ANALYSIS_ONLY_FIELDS = frozenset(("colorMap",))
    SOURCE_REPORTS = frozenset(
        (
            "laserPulseAnimation",
            "laserPulse2Animation",
        )
    )

    @classmethod
    def fixup_old_data(cls, data, qcall, **kwargs):
        dm = data.models
        cls._init_models(
            dm,
            (
                "crystalAnimation",
                "crystal3dAnimation",
                "crystalCylinder",
                "crystalSettings",
                "laserPulse",
                "laserPulseAnimation",
                "laserPulse2Animation",
                "initialIntensityReport",
                "plotAnimation",
                "plot2Animation",
                "simulation",
            ),
        )
        for n in dm:
            if "beamlineAnimation" in n:
                if "dataType" in dm[n]:
                    del dm[n]["dataType"]
                cls.update_model_defaults(dm[n], cls.WATCHPOINT_REPORT)
        for m in dm.beamline:
            if m.type == "crystal" and "n0" in m and not isinstance(m.n0, list):
                del m["n0"]
                if "n2" in m:
                    del m["n2"]
            cls.update_model_defaults(m, m.type)

    @classmethod
    def _compute_model(cls, analysis_model, *args, **kwargs):
        if analysis_model in (
            "crystalAnimation",
            "crystal3dAnimation",
            "plotAnimation",
            "plot2Animation",
        ):
            return "crystalAnimation"
        if "beamlineAnimation" in analysis_model:
            return "beamlineAnimation"
        if analysis_model in cls.SOURCE_REPORTS:
            return "laserPulseAnimation"
        return super(SimData, cls)._compute_model(analysis_model, *args, **kwargs)

    @classmethod
    def _compute_job_fields(cls, data, r, compute_model):
        return []

    @classmethod
    def _lib_file_basenames(cls, data):
        res = []
        if data.models.laserPulse.distribution == "file":
            for f in ("ccd", "meta", "wfs"):
                res.append(
                    cls.lib_file_name_with_model_field(
                        "laserPulse", f, data.models.laserPulse[f]
                    )
                )
        return res
