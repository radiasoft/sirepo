# -*- coding: utf-8 -*-
"""rftrack simulation data operations

:copyright: Copyright (c) 2026 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
import sirepo.sim_data.lattice


class SimData(sirepo.sim_data.lattice.LatticeSimData):
    _BUNCH_REPORT_DEPENDENCIES = ["beam"]

    @classmethod
    def _lib_file_basenames(cls, data):
        # LatticeSimData._lib_file_basenames() only scans lattice elements
        # (CAVITY/SOLENOID field maps) for InputFile fields; beam.
        # distributionFile lives on a different (non-element) model, so it
        # has to be added explicitly or the file never gets copied into the
        # run directory.
        res = super()._lib_file_basenames(data)
        b = data.models.beam
        if b.distributionType == "fromFile" and b.distributionFile:
            res.append(
                cls.lib_file_name_with_model_field(
                    "beam", "distributionFile", b.distributionFile
                )
            )
        return res

    @classmethod
    def fixup_old_data(cls, data, qcall, **kwargs):
        super().fixup_old_data(data, qcall, **kwargs)
        cls._init_models(
            data.models,
            (
                "beam",
                "beamline",
                "simulation",
                "simulationSettings",
                "simulationStatus",
                "statAnimation",
            ),
        )
        if not data.models.beam.get("randomSeed"):
            # randomSeed was briefly an OptionalInteger (default "") before
            # becoming a required Integer defaulting to RF_Track's own
            # mt19937 default seed (5489, see rftrack.py); _init_models()
            # only backfills missing keys, not an already-saved "".
            data.models.beam.randomSeed = 5489
