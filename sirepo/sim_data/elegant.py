# -*- coding: utf-8 -*-
"""elegant simulation data functions

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
from sirepo.template import lattice
from sirepo.template.lattice import LatticeUtil
import re
import sirepo.sim_data


class SimData(sirepo.sim_data.SimDataBase):
    @classmethod
    def fixup_old_data(cls, data, qcall, **kwargs):
        s = cls.schema()
        dm = data.models
        cls._init_models(
            dm, ("bunch", "bunchFile", "bunchSource", "simulation", "twissReport")
        )
        dm.setdefault("rpnVariables", [])
        for m in dm.elements:
            if m.type == "WATCH":
                m.filename = "1"
                if m.mode == "coordinates" or m.mode == "coord":
                    m.mode = "coordinate"
            cls.update_model_defaults(m, m.type)
        for m in dm.commands:
            cls.update_model_defaults(m, "command_{}".format(m._type))
        cls._organize_example(data)
        from sirepo.template.elegant import OutputFileIterator

        LatticeUtil.fixup_output_files(data, s, OutputFileIterator(True))

    @classmethod
    def _compute_job_fields(cls, data, r, compute_model):
        res = []
        if compute_model in ("twissReport", "bunchReport"):
            res += ["bunch", "bunchSource", "bunchFile", "rpnVariables"]
        if r == "twissReport":
            res += ["elements", "beamlines", "commands", "simulation.activeBeamlineId"]
        return res

    @classmethod
    def _compute_model(cls, analysis_model, *args, **kwargs):
        if "bunchReport" in analysis_model:
            return "bunchReport"
        return super(SimData, cls)._compute_model(analysis_model, *args, **kwargs)

    @classmethod
    def _lib_file_basenames(cls, data):
        res = (
            LatticeUtil(data, cls.schema())
            .iterate_models(lattice.InputFileIterator(cls))
            .result
        )
        if data.models.bunchFile.sourceFile:
            res.append(
                cls.lib_file_name_with_model_field(
                    "bunchFile", "sourceFile", data.models.bunchFile.sourceFile
                )
            )
        return res
