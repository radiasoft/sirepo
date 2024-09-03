# -*- coding: utf-8 -*-
"""opal simulation data operations

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
        dm = data.models
        dm.setdefault("rpnVariables", [])
        if "elementPosition" not in dm.simulation:
            # old simulations use 'relative', new ones use 'absolute'
            dm.simulation.elementPosition = "relative"
        cls._init_models(
            dm,
            (
                "beamline3dAnimation",
                "bunchAnimation",
                "plotAnimation",
                "plot2Animation",
            ),
        )
        for cmd in dm.commands:
            if cmd._type == "filter":
                cmd.type = cmd.type.upper()
            elif cmd._type == "particlematterinteraction":
                if cmd.type not in [
                    t[0] for t in cls.schema().enum.ParticlematterinteractionType
                ]:
                    cmd.type = ""
                cmd.material = cmd.material.upper()
        if "bunchReport1" not in dm:
            for i in range(1, 5):
                m = dm["bunchReport{}".format(i)] = PKDict()
                cls.update_model_defaults(m, "bunchReport")
                if i == 1:
                    m.y = "px"
                elif i == 2:
                    m.x = "y"
                    m.y = "py"
                elif i == 4:
                    m.x = "z"
                    m.y = "pz"
        if "aspectRatio" in dm.plotAnimation:
            del dm.plotAnimation["aspectRatio"]
        for bl in dm.beamlines:
            cls.update_model_defaults(bl, "beamline")
        cls._remove_deprecated_items(dm)

    @classmethod
    def _compute_model(cls, analysis_model, *args, **kwargs):
        if "bunchReport" in analysis_model:
            return "bunchReport"
        return super(SimData, cls)._compute_model(analysis_model, *args, **kwargs)

    @classmethod
    def _compute_job_fields(cls, data, r, compute_model):
        if "bunchReport" in r:
            return ["commands", "rpnVariables"]
        return []

    @classmethod
    def _lib_file_basenames(cls, data):
        return (
            LatticeUtil(data, cls.schema())
            .iterate_models(lattice.InputFileIterator(cls))
            .result
        )

    @classmethod
    def _remove_deprecated_items(cls, models):
        cmds = []
        deprecated_cmds = set(
            [
                "attlist",
                "eigen",
                "envelope",
                "list",
                "matrix",
                "micado",
                "start",
                "survey",
                "threadall",
                "threadbpm",
                "twiss",
                "twiss3",
                "twisstrack",
            ]
        )
        for cmd in models.commands:
            if cmd._type not in deprecated_cmds:
                cmds.append(cmd)
        models.commands = cmds
        elements = []
        deprecated_elements = set(
            [
                "CYCLOTRONVALLEY",
                "HMONITOR",
                "INSTRUMENT",
                "MULTIPOLETCURVEDCONSTRADIUS",
                "MULTIPOLETCURVEDVARRADIUS",
                "MULTIPOLETSTRAIGHT",
                "PARALLELPLATE",
                "PATCH",
                "PEPPERPOT",
                "SLIT",
                "SROT",
                "SEPARATOR",
                "STRIPPER",
                "VMONITOR",
                "WIRE",
                "YROT",
            ]
        )
        removed_ids = []
        for el in models.elements:
            if el.type in deprecated_elements:
                removed_ids.append(el._id)
            else:
                elements.append(el)
        for bl in models.beamlines:
            items = []
            for item in bl["items"]:
                if item not in removed_ids:
                    items.append(item)
            bl["items"] = items
        models.elements = elements
        if "twissReport" in models:
            del models["twissReport"]
