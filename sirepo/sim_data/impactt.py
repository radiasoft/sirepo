# -*- coding: utf-8 -*-
"""simulation data operations
:copyright: Copyright (c) 2024 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
import sirepo.sim_data.lattice


class SimData(sirepo.sim_data.lattice.LatticeSimData):
    _BUNCH_REPORT_DEPENDENCIES = ["beam", "distgen", "distribution", "rpnVariables"]

    @classmethod
    def fixup_old_data(cls, data, qcall, **kwargs):
        super().fixup_old_data(data, qcall, **kwargs)
        cls._init_models(
            data.models,
            (
                "beam",
                "beamline",
                "distgen",
                "distribution",
                "simulation",
                "simulationSettings",
                "statAnimation",
            ),
        )

    @classmethod
    def get_distgen_file(cls, data, require_exists=False):
        return cls.__lib_file(
            data, "distgen_xyfile", "distgen", "xy_dist_file", require_exists
        )

    @classmethod
    def get_distribution_file(cls, data, require_exists=False):
        return cls.__lib_file(data, "16", "distribution", "filename", require_exists)

    @classmethod
    def _lib_file_basenames(cls, data):
        return super()._lib_file_basenames(data) + [
            f
            for f in (cls.get_distribution_file(data), cls.get_distgen_file(data))
            if f
        ]

    @classmethod
    def __lib_file(cls, data, flagdist, model_name, field_name, require_exists):
        if (
            data.models.distribution.Flagdist == flagdist
            and data.models[model_name][field_name]
        ):
            return cls.lib_file_name_with_model_field(
                model_name, field_name, data.models[model_name][field_name]
            )
        if require_exists:
            raise AssertionError(f"Missing {model_name} {field_name}")
        return None
