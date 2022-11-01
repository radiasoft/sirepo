# -*- coding: utf-8 -*-
"""simulation data operations

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
from sirepo.template.lattice import LatticeUtil
from sirepo.template.template_common import ParticleEnergy
import math
import numpy
import re
import sirepo.sim_data
import sirepo.simulation_db


class SimData(sirepo.sim_data.SimDataBase):
    @classmethod
    def add_ptc_track_commands(cls, data):
        def _set_ptc_ids(ptc_commands, data):
            m = LatticeUtil.max_id(data) + 1
            for i, c in enumerate(ptc_commands):
                c._id = m + i
            return ptc_commands

        data.models.bunch.beamDefinition = "gamma"
        data.models.commands.extend(
            _set_ptc_ids(
                [
                    PKDict(_type="ptc_create_universe"),
                    PKDict(_type="ptc_create_layout"),
                    PKDict(_type="ptc_track", file="1", icase="6"),
                    PKDict(_type="ptc_track_end"),
                    PKDict(_type="ptc_end"),
                ],
                data,
            )
        )

    @classmethod
    def beamline_elements(cls, madx):
        elmap = PKDict({e._id: e for e in madx.elements})
        for el_id in madx.beamlines[0]["items"]:
            yield elmap[el_id]

    @classmethod
    def controls_madx_dir(cls):
        return sirepo.simulation_db.simulation_dir("madx")

    @classmethod
    def current_field(cls, kick_field):
        return "current_{}".format(kick_field)

    @classmethod
    def default_optimizer_settings(cls, madx):
        targets = []
        for el in cls.beamline_elements(madx):
            if el.type in ("MONITOR", "HMONITOR", "VMONITOR"):
                item = cls.model_defaults("optimizerTarget")
                item.name = el.name
                if el.type == "HMONITOR":
                    del item["y"]
                elif el.type == "VMONITOR":
                    del item["x"]
                targets.append(item)
        opts = cls.model_defaults("optimizerSettings").pkupdate(
            PKDict(
                targets=targets,
            )
        )
        cls.init_optimizer_inputs(opts, madx)
        return opts

    @classmethod
    def fixup_old_data(cls, data, qcall, **kwargs):
        dm = data.models
        cls._init_models(
            dm,
            (
                "beamPositionAnimation",
                "bunch",
                "command_beam",
                "dataFile",
                "deviceServerMonitor",
                "initialMonitorPositionsReport",
                "instrumentAnimationAll",
                "instrumentAnimationTwiss",
            ),
        )
        if "externalLattice" in dm:
            sirepo.sim_data.get_class("madx").fixup_old_data(
                dm.externalLattice, qcall=qcall
            )
            if "optimizerSettings" not in dm:
                dm.optimizerSettings = cls.default_optimizer_settings(
                    dm.externalLattice.models
                )
            if "controlSettings" not in dm:
                cls.init_process_variables(dm)
                cls.init_currents(dm.command_beam, dm.externalLattice.models)
            cls._init_models(dm, ("controlSettings", "optimizerSettings"))
            if "inputs" not in dm.optimizerSettings:
                cls.init_optimizer_inputs(
                    dm.optimizerSettings, dm.externalLattice.models
                )
            cls._remove_old_command(dm.externalLattice.models)
        if (
            dm.command_beam.gamma == 0
            and "pc" in dm.command_beam
            and dm.command_beam.pc > 0
        ):
            cls.update_beam_gamma(dm.command_beam)
            dm.command_beam.pc = 0
        if "command_twiss" in dm:
            for f in dm.command_twiss:
                if f in dm.bunch:
                    dm.bunch[f] = dm.command_twiss[f]
            del dm["command_twiss"]
            if "externalLattice" in dm:
                cls.add_ptc_track_commands(dm.externalLattice)

    @classmethod
    def init_optimizer_inputs(cls, optimizerSettings, madx):
        optimizerSettings.inputs = PKDict(kickers=PKDict(), quads=PKDict())
        for el in cls.beamline_elements(madx):
            if el.type == "QUADRUPOLE":
                optimizerSettings.inputs.quads[str(el._id)] = False
            elif "KICKER" in el.type:
                optimizerSettings.inputs.kickers[str(el._id)] = True

    @classmethod
    def init_currents(cls, beam, models):
        def is_kick_field(field):
            return re.search(r"^(.?kick|k1)$", field)

        ac = AmpConverter(beam)
        for el in cls.beamline_elements(models):
            for f in list(el.keys()):
                if is_kick_field(f):
                    el[cls.current_field(f)] = ac.kick_to_current(el[f])

    @classmethod
    def init_process_variables(cls, models):
        pvs = []

        def _add_pv(elId, dim, write="0"):
            pvs.append(
                PKDict(
                    elId=elId,
                    pvDimension=dim,
                    isWritable=write,
                    pvName="",
                )
            )

        models.controlSettings = cls.model_defaults("controlSettings").pkupdate(
            {
                "processVariables": pvs,
            }
        )
        for el in cls.beamline_elements(models.externalLattice.models):
            if el.type == "MONITOR":
                _add_pv(el._id, "horizontal")
                _add_pv(el._id, "vertical")
            elif el.type == "HMONITOR":
                _add_pv(el._id, "horizontal")
            elif el.type == "VMONITOR":
                _add_pv(el._id, "vertical")
            elif el.type == "KICKER":
                _add_pv(el._id, "horizontal")
                _add_pv(el._id, "horizontal", "1")
                _add_pv(el._id, "vertical")
                _add_pv(el._id, "vertical", "1")
            elif el.type == "HKICKER":
                _add_pv(el._id, "horizontal")
                _add_pv(el._id, "horizontal", "1")
            elif el.type == "VKICKER":
                _add_pv(el._id, "vertical")
                _add_pv(el._id, "vertical", "1")
            elif el.type == "QUADRUPOLE":
                _add_pv(el._id, "none")
        return models

    @classmethod
    def update_beam_gamma(cls, beam):
        beam.gamma = ParticleEnergy.compute_energy(
            "madx",
            beam.particle,
            beam,
        ).gamma

    @classmethod
    def _compute_job_fields(cls, data, r, compute_model):
        res = []
        if r == "initialMonitorPositionsReport":
            res = ["controlSettings", "dataFile", "externalLattice"]
        return res

    @classmethod
    def _compute_model(cls, analysis_model, *args, **kwargs):
        if "instrument" in analysis_model or analysis_model == "beamPositionAnimation":
            return "instrumentAnimation"
        return super(SimData, cls)._compute_model(analysis_model, *args, **kwargs)

    @classmethod
    def _lib_file_basenames(cls, data):
        if "controlSettings" in data.models:
            n = data.models.controlSettings.inputLogFile
            if n:
                return [
                    cls.lib_file_name_with_model_field(
                        "controlSettings", "inputLogFile", n
                    )
                ]
        return []

    @classmethod
    def _remove_old_command(cls, dm):
        cmds = []
        for cmd in dm.commands:
            if cmd._type == "select" or cmd._type == "twiss":
                continue
            cmds.append(cmd)
        dm.commands = cmds


class AmpConverter:
    _GEV_TO_KG = 1.78266192e-27
    # Coulomb
    _ELEMENTARY_CHARGE = 1.602176634e-19
    _SCHEMA = SimData.schema()

    def __init__(self, beam, amp_table=None, default_factor=100):
        if amp_table and len(amp_table[0]) < 2:
            raise AssertionError("invalid amp_table: {}".format(amp_table))
        self._computed_reverse_table = False
        self._amp_table = [r for r in map(lambda x: [x[0], x[1]], amp_table or [])]
        self._beam_info = self.__beam_info(beam)
        self._default_factor = default_factor

    def current_to_kick(self, current):
        return self.__compute_kick(current, self.__interpolate_table(current, 0, 1))

    def kick_to_current(self, kick):
        if not self._computed_reverse_table:
            self._computed_reverse_table = True
            self.__build_reverse_map()
        return self.__compute_current(float(kick), self.__interpolate_table(kick, 2, 1))

    def __beam_info(self, beam):
        if beam.get("particle") and self._SCHEMA.constants.particleMassAndCharge.get(
            beam.particle
        ):
            pmc = self._SCHEMA.constants.particleMassAndCharge.get(beam.particle)
        else:
            pmc = [beam.mass, beam.charge]
        return PKDict(
            mass=pmc[0] * self._GEV_TO_KG,
            charge=pmc[1] * self._ELEMENTARY_CHARGE,
            gamma=beam.gamma,
            beta=math.sqrt(1 - (1 / (beam.gamma * beam.gamma))),
        )

    def __build_reverse_map(self):
        if self._amp_table:
            for row in self._amp_table:
                row.append(self.__compute_kick(row[0], row[1]))

    def __compute_current(self, kick, factor):
        b = self._beam_info
        return (
            kick
            * b.gamma
            * b.mass
            * b.beta
            * self._SCHEMA.constants.clight
            / (b.charge * factor)
        )

    def __compute_kick(self, current, factor):
        b = self._beam_info
        return (
            current
            * b.charge
            * factor
            / (b.gamma * b.mass * b.beta * self._SCHEMA.constants.clight)
        )

    def __interpolate_table(self, value, from_index, to_index):
        if not self._amp_table:
            return self._default_factor
        table = numpy.vstack(self._amp_table)
        return numpy.interp(value, table[:, from_index], table[:, to_index])
