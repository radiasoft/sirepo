# -*- coding: utf-8 -*-
"""simulation data operations

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkcollections
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
import sirepo.sim_data


class SimData(sirepo.sim_data.SimDataBase):
    ANALYSIS_ONLY_FIELDS = frozenset(("colorMap", "notes"))

    @classmethod
    def fixup_old_data(cls, data, qcall, **kwargs):
        dm = data.models
        cls._init_models(
            dm,
            (
                "animation",
                "beamAnimation",
                "beamPreviewReport",
                "electronBeam",
                "fieldAnimation",
                "laserPreviewReport",
                "particleAnimation",
                "simulationGrid",
            ),
        )
        pkcollections.unchecked_del(
            dm.simulationGrid,
            "xMin",
            "xMax",
            "xCount",
            "zLambda",
        )
        if "rmsRadius" in dm.electronBeam and dm.electronBeam.rmsRadius == 0:
            del dm.electronBeam["rmsRadius"]
        cls._organize_example(data)

    @classmethod
    def _compute_job_fields(cls, data, r, compute_model):
        if r not in ("beamPreviewReport", "laserPreviewReport"):
            return []
        return cls._non_analysis_fields(data, r) + [
            "simulation.sourceType",
            "electronBeam",
            "electronPlasma",
            "laserPulse",
            "simulationGrid",
        ]

    @classmethod
    def _lib_file_basenames(cls, data):
        return []
