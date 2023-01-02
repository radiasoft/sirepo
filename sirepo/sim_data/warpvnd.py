# -*- coding: utf-8 -*-
"""simulation data operations

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkcollections
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
from pykern.pkdebug import pkdp
import re
import sirepo.sim_data


class SimData(sirepo.sim_data.SimDataBase):
    ANALYSIS_ONLY_FIELDS = frozenset(
        ("colorMap", "notes", "color", "impactColorMap", "axes", "slice")
    )

    @classmethod
    def _compute_model(cls, analysis_model, *args, **kwargs):
        if analysis_model in (
            "currentAnimation",
            "egunCurrentAnimation",
            "fieldAnimation",
            "impactDensityAnimation",
            "particle3d",
            "particleAnimation",
        ):
            return "animation"
        if analysis_model == "optimizerAnimation":
            return analysis_model
        if analysis_model in (
            "fieldCalcAnimation",
            "fieldCalculationAnimation",
            "fieldComparisonAnimation",
        ):
            return "fieldCalculationAnimation"
        # TODO(pjm): special case, should be an Animation model
        if analysis_model == "particle3d":
            return "animation"
        return super(SimData, cls)._compute_model(analysis_model, *args, **kwargs)

    @classmethod
    def fixup_old_data(cls, data, qcall, **kwargs):
        def _fixup_reflector(m):
            if "isReflector" not in m:
                return
            if m.isReflector == "1":
                for f in "specProb", "diffProb":
                    m[f] = float(m[f])
                if m.specProb > 0:
                    m.reflectorType = "specular"
                    m.reflectorProbability = m.specProb
                elif m.diffProb > 0:
                    m.reflectorType = "diffuse"
                    m.reflectorProbability = m.diffProb
            for f in ("isReflector", "specProb", "diffProb", "refScheme"):
                del m[f]

        dm = data.models
        dm.pksetdefault(optimizer=PKDict)
        dm.optimizer.pksetdefault(
            constraints=list,
            enabledFields=PKDict,
            fields=list,
        )
        cls._init_models(
            dm,
            (
                # simulationGrid must be first
                "simulationGrid",
                "anode",
                "egunCurrentAnimation",
                "fieldAnimation",
                "fieldCalcAnimation",
                "fieldCalculationAnimation",
                "fieldComparisonAnimation",
                "fieldComparisonReport",
                "fieldReport",
                "impactDensityAnimation",
                "optimizer",
                "optimizerAnimation",
                "optimizerStatus",
                "particle3d",
                "particleAnimation",
                "simulation",
                "cathode",
            ),
            dynamic=lambda m: cls.__dynamic_defaults(data, m),
        )
        pkcollections.unchecked_del(dm.particle3d, "joinEvery")
        for m in ("anode", "cathode"):
            _fixup_reflector(dm[m])
        s = cls.schema()
        for c in dm.conductorTypes:
            x = c.setdefault("isConductor", "1" if c.voltage > 0 else "0")
            # conductor.color is null is examples
            if not c.get("color", 0):
                c.color = s.constants[
                    "zeroVoltsColor" if x == "0" else "nonZeroVoltsColor"
                ]
            cls.update_model_defaults(c, c.type)
            _fixup_reflector(c)
        for c in dm.conductors:
            cls.update_model_defaults(c, "conductorPosition")
        if dm.optimizer.objective == "efficiency":
            dm.optimizer.objective = "transparency"
        cls._organize_example(data)

    @classmethod
    def warpvnd_is_3d(cls, data):
        return data.models.simulationGrid.simulation_mode == "3d"

    @classmethod
    def _compute_job_fields(cls, data, r, compute_model):
        res = ["simulationGrid"]
        res.append(cls.__non_opt_fields_to_array(data.models.beam))
        for container in ("conductors", "conductorTypes"):
            for m in data.models[container]:
                res.append(cls.__non_opt_fields_to_array(m))
        return res + cls._non_analysis_fields(data, r)

    @classmethod
    def __dynamic_defaults(cls, data, model):
        """defaults that depend on the current data"""
        if not model.startswith("fieldComparison"):
            return PKDict()
        g = data.models.simulationGrid
        t = cls.warpvnd_is_3d(data)
        return PKDict(
            dimension="x",
            xCell1=0,
            xCell2=int(g.num_x / 2.0),
            xCell3=g.num_x,
            yCell1=0,
            yCell2=int(g.num_y / 2.0) if t else 0,
            yCell3=g.num_y if t else 0,
            zCell1=0,
            zCell2=int(g.num_z / 2.0),
            zCell3=g.num_z,
        )

    @classmethod
    def _lib_file_basenames(cls, data):
        res = []
        for m in data.models.conductorTypes:
            if m.type == "stl":
                res.append(cls.lib_file_name_with_model_field("stl", "file", m.file))
        return res

    @classmethod
    def __non_opt_fields_to_array(cls, model):
        res = []
        for f in model:
            if not re.search(r"\_opt$", f) and f not in cls.ANALYSIS_ONLY_FIELDS:
                res.append(model[f])
        return res
