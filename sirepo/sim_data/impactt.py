# -*- coding: utf-8 -*-
"""simulation data operations
:copyright: Copyright (c) 2024 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkdebug import pkdc, pkdlog, pkdp
import sirepo.sim_data
import sirepo.template.lattice


class SimData(sirepo.sim_data.SimDataBase):
    @classmethod
    def fixup_old_data(cls, data, qcall, **kwargs):
        dm = data.models
        cls._init_models(
            dm,
            (
                "beam",
                "beamline",
                "distgen",
                "distribution",
                "simulation",
                "simulationSettings",
                "statAnimation",
            ),
        ),
        dm.setdefault("rpnVariables", [])

    @classmethod
    def get_distgen_file(cls, data, require_exists=False):
        return cls.__lib_file(
            data, "distgen_xyfile", "distgen", "xy_dist_file", require_exists
        )

    @classmethod
    def get_distribution_file(cls, data, require_exists=False):
        return cls.__lib_file(data, "16", "distribution", "filename", require_exists)

    @classmethod
    def _compute_job_fields(cls, data, *args, **kwargs):
        return [data.report]

    @classmethod
    def _lib_file_basenames(cls, data):
        return [
            f
            for f in (cls.get_distribution_file(data), cls.get_distgen_file(data))
            if f
        ] + sirepo.template.lattice.LatticeUtil(data, cls.schema()).iterate_models(
            sirepo.template.lattice.InputFileIterator(cls)
        ).result

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
