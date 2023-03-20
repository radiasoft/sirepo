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

_RESULTS_FILE = "results.h5"

class SimData(sirepo.sim_data.SimDataBase):
    ANALYSIS_ONLY_FIELDS = frozenset(
        (
            "colorMap",
        )
    )

    @classmethod
    def fixup_old_data(cls, data, qcall, **kwargs):
        dm = data.models
        cls._init_models(
            dm,
            (
                "crystal",
                "crystalAnimation",
                "crystal3dAnimation",
                "crystalCylinder",
                "crystalSettings",
                "gaussianBeam",
                "laserPulse",
                "initialIntensityReport",
                "initialPhaseReport",
                "lens",
                "plotAnimation",
                "plot2Animation",
                "simulation",
                "simulationSettings",
                "watch",
                "watchpointReport",
                "wavefrontSummaryAnimation",
            ),
        )
        for m in dm.beamline:
            cls.update_model_defaults(m, m.type)

    @classmethod
    def get_watchpoint(cls, data):
        r = data.report
        w_id = int(r.replace(cls.WATCHPOINT_REPORT, ""))
        return [e for e in data.models.beamline if e.id == w_id][0]

    @classmethod
    def h5_data_file(cls, element=None):
        return f"{element.type}_{element.id}.h5" if element else _RESULTS_FILE

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
        if r in INITIAL_REPORTS:
            res += cls._non_analysis_fields(data, "laserPulse")
        if cls.is_watchpoint(r):
            res += ["initialIntensityReport.aspect"]
        return res

    @classmethod
    def _lib_file_basenames(cls, data):
        res = []
        if data.report in INITIAL_REPORTS and data.models.laserPulse.geometryFromFiles == "1":
            for f in ("ccd", "meta", "wfs"):
                res.append(
                    cls.lib_file_name_with_model_field(
                        "laserPulse", f, data.models.laserPulse[f]
                    )
                )
        return res

    @classmethod
    def _sim_file_basenames(cls, data):
        res = []
        if cls.is_watchpoint(data.report):
            res.append(
                PKDict(
                    basename=cls.h5_data_file(cls.get_watchpoint(data))
                )
            )
        return res
