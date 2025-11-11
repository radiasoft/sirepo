# -*- coding: utf-8 -*-
"""opal simulation data operations

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
import sirepo.sim_data.lattice
import re


class SimData(sirepo.sim_data.lattice.LatticeSimData):
    _BUNCH_REPORT_DEPENDENCIES = ["commands", "rpnVariables"]

    @classmethod
    def fixup_old_data(cls, data, qcall, **kwargs):
        super().fixup_old_data(data, qcall, **kwargs)
        dm = data.models
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
        if "aspectRatio" in dm.plotAnimation:
            del dm.plotAnimation["aspectRatio"]
        for bl in dm.beamlines:
            cls.update_model_defaults(bl, "beamline")
        cls._remove_deprecated_items(dm)

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
