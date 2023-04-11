# -*- coding: utf-8 -*-
"""SILAS simulation data operations

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
import sirepo.sim_data

INITIAL_REPORTS = frozenset(
    (
        "initialIntensityReport",
        "initialPhaseReport",
    )
)

WATCHPOINT_REPORT = "watchpointReport"


class SimData(sirepo.sim_data.SimDataBase):
    ANALYSIS_ONLY_FIELDS = frozenset(("colorMap",))

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
                "initialIntensityReport",
                "initialPhaseReport",
                "plotAnimation",
                "plot2Animation",
                "simulation",
                "watchpointReport",
            ),
        )
        for m in dm.beamline:
            if m.type == "crystal" and "n0" in m and not isinstance(m.n0, list):
                del m["n0"]
                if "n2" in m:
                    del m["n2"]
            cls.update_model_defaults(m, m.type)

    @classmethod
    def initial_reports(cls):
        return INITIAL_REPORTS

    @classmethod
    def is_watchpoint(cls, name):
        return cls.WATCHPOINT_REPORT in name

    @classmethod
    def _compute_model(cls, analysis_model, *args, **kwargs):
        if analysis_model in (
            "crystalAnimation",
            "crystal3dAnimation",
            "plotAnimation",
            "plot2Animation",
        ):
            return "crystalAnimation"
        return super(SimData, cls)._compute_model(analysis_model, *args, **kwargs)

    @classmethod
    def _compute_job_fields(cls, data, r, compute_model):
        res = []
        if r in INITIAL_REPORTS or cls.is_watchpoint(r):
            res += ["laserPulse"] + cls._non_analysis_fields(data, r)
            if cls.is_watchpoint(r):
                res.append("beamline")
        return res

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
