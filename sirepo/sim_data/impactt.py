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
                "distribution",
                "simulation",
                "simulationSettings",
                "statAnimation",
            ),
        ),
        dm.setdefault("rpnVariables", [])

    @classmethod
    def _compute_job_fields(cls, data, *args, **kwargs):
        return [data.report]

    @classmethod
    def _lib_file_basenames(cls, data):
        return (
            sirepo.template.lattice.LatticeUtil(data, cls.schema())
            .iterate_models(sirepo.template.lattice.InputFileIterator(cls))
            .result
        )
