# -*- coding: utf-8 -*-
"""simulation data operations

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
import sirepo.sim_data
import scipy.constants


class SimData(sirepo.sim_data.SimDataBase):
    ANALYSIS_ONLY_FIELDS = frozenset(("colorMap", "notes", "aspectRatio"))

    @classmethod
    def fixup_old_data(cls, data, qcall, **kwargs):
        dm = data.models
        if not isinstance(dm.beamline, list):
            raise AssertionError("models.beamline is in the incorrect format")
        cls._init_models(
            dm,
            (
                "beamStatisticsReport",
                "bendingMagnet",
                "histogramReport",
                "initialIntensityReport",
                "plotXYReport",
                "undulator",
                "undulatorBeam",
            ),
        )
        if "magneticField" not in dm.bendingMagnet:
            dm.bendingMagnet.magneticField = (
                1e9
                / scipy.constants.c
                * float(dm.electronBeam.bener)
                / float(dm.bendingMagnet.r_magnet)
            )
        for m in dm:
            if cls.is_watchpoint(m):
                cls.update_model_defaults(dm[m], "watchpointReport")
        for m in dm.beamline:
            cls.update_model_defaults(m, m.type)
        cls._organize_example(data)

    @classmethod
    def shadow_simulation_files(cls, data):
        m = data.models
        if m.simulation.sourceType == "wiggler" and m.wiggler.b_from in ("1", "2"):
            return [cls.shadow_wiggler_file(m.wiggler.trajFile)]
        return []

    @classmethod
    def shadow_wiggler_file(cls, value):
        return cls.lib_file_name_with_model_field("wiggler", "trajFile", value)

    @classmethod
    def _compute_job_fields(cls, data, r, compute_model):
        assert r in data.models, f"unknown report: {r}"
        res = cls._non_analysis_fields(data, r) + [
            "bendingMagnet",
            "electronBeam",
            "geometricSource",
            "rayFilter",
            "simulation.istar1",
            "simulation.npoint",
            "simulation.sourceType",
            "sourceDivergence",
            "undulator",
            "undulatorBeam",
            "wiggler",
        ]
        if r == "initialIntensityReport" and data["models"]["beamline"]:
            res.append([data["models"]["beamline"][0]["position"]])
        # TODO(pjm): only include items up to the current watchpoint
        if cls.is_watchpoint(r) or r == "beamStatisticsReport":
            res.append("beamline")
        return res

    @classmethod
    def _lib_file_basenames(cls, data, *args, **kwargs):
        return cls.shadow_simulation_files(data)
