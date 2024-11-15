# -*- coding: utf-8 -*-
"""Convert codes to/from MAD-X.

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
from sirepo import simulation_db
from sirepo.template import madx_parser
from sirepo.template.lattice import LatticeUtil
from sirepo.template.template_common import ParticleEnergy
import copy
import sirepo.sim_data
import sirepo.template


class MadxConverter:
    _MADX_VARIABLES = PKDict(
        twopi="pi * 2",
        raddeg="pi / 180",
        degrad="180 / pi",
    )

    def __init__(self, sim_type, field_map, downcase_variables=False, qcall=None):
        self.sim_type = sim_type
        self.downcase_variables = downcase_variables
        self.full_field_map = self._build_field_map(field_map)
        self.qcall = qcall

    def fill_in_missing_constants(self, data, constants):
        import sirepo.template.madx
        import ast

        class Visitor(ast.NodeVisitor):
            def visit_Name(self, node):
                return node.id

        n = [v.name for v in data.models.rpnVariables]
        for v in data.models.rpnVariables:
            values = set()
            if type(v.value) == str:
                tree = ast.parse(v.value)
                for node in ast.walk(tree):
                    values.add(Visitor().visit(node))
            for c in sirepo.template.madx.MADX_CONSTANTS.keys() - constants.keys():
                if type(v.value) == str and c in values and c not in n:
                    data.models.rpnVariables.insert(
                        0, PKDict(name=c, value=sirepo.template.madx.MADX_CONSTANTS[c])
                    )
                    n.append(c)
        return data

    def from_madx(self, data):
        from sirepo.template import madx

        self.__init_direction(data, madx.SIM_TYPE, self.sim_type)
        self.field_map = self.full_field_map.from_madx
        self.drift_type = "DRIFT"
        return self._convert(self.__normalize_madx_beam(data))

    def from_madx_text(self, text):
        return self.from_madx(madx_parser.parse_file(text, self.downcase_variables))

    def to_madx(self, data):
        from sirepo.template import madx

        self.__init_direction(data, self.sim_type, madx.SIM_TYPE)
        self.field_map = self.full_field_map.to_madx
        self.drift_type = self.full_field_map.from_madx.DRIFT[0]
        return self._convert(data)

    def to_madx_text(self, data):
        from sirepo.template import madx

        return madx.python_source_for_model(
            self.to_madx(data),
            model=None,
            qcall=self.qcall,
        )

    def _build_field_map(self, field_map):
        res = PKDict(
            from_madx=PKDict(),
            to_madx=PKDict(),
        )
        for el in field_map:
            madx_name = el[0]
            res.from_madx[madx_name] = el[1]
            for idx in range(1, len(el)):
                fields = copy.copy(el[idx])
                name = fields[0]
                if name not in res.to_madx:
                    fields[0] = madx_name
                    res.to_madx[name] = fields
        return res

    def _convert(self, data):
        self.result = simulation_db.default_data(self.to_class.sim_type())
        self._copy_beamlines(data)
        self._copy_elements(data)
        self._copy_code_variables(data)
        LatticeUtil(
            self.result,
            self.to_class.schema(),
        ).sort_elements_and_beamlines()
        return self.result

    def _copy_beamlines(self, data):
        for bl in data.models.beamlines:
            self.result.models.beamlines.append(
                PKDict(
                    name=bl.name,
                    items=bl["items"],
                    id=bl.id,
                )
            )
        for f in ("name", "visualizationBeamlineId", "activeBeamlineId"):
            if f in data.models.simulation:
                self.result.models.simulation[f] = data.models.simulation[f]

    def _copy_code_variables(self, data):
        res = copy.deepcopy(data.models.rpnVariables)
        if self.to_class.sim_type() in ("madx", "opal"):
            res = list(filter(lambda x: x.name not in self._MADX_VARIABLES, res))
        else:
            names = set([v.name for v in res])
            for name in self._MADX_VARIABLES:
                if name not in names:
                    res.append(
                        PKDict(
                            name=name,
                            value=self._MADX_VARIABLES[name],
                        )
                    )
        self.result.models.rpnVariables = res

    def _copy_elements(self, data):
        for el in data.models.elements:
            el = copy.deepcopy(el)
            if el.type not in self.field_map:
                pkdlog("Unhandled element type: {}", el.type)
                el.type = self.drift_type
                if "l" not in el:
                    el.l = 0
            fields = self.field_map[el.type]
            values = PKDict(
                name=el.name,
                type=fields[0],
                _id=el._id,
            )
            for idx in range(1, len(fields)):
                f1 = f2 = fields[idx]
                if "=" in fields[idx]:
                    f1, f2 = fields[idx].split("=")
                    if self.to_class.sim_type() == "madx":
                        f2, f1 = f1, f2
                values[f1] = el[f2]
            self._fixup_element(el, values)
            self.to_class.update_model_defaults(values, values.type)
            self.result.models.elements.append(values)

    def _find_var(self, data, name):
        name = self._var_name(name)
        for v in data.models.rpnVariables:
            if v.name == name:
                return v
        return None

    def _fixup_element(self, element_in, element_out):
        pass

    def _remove_zero_drifts(self, data):
        z = set()
        e = []
        for el in data.models.elements:
            if el.type == "DRIFT" and el.l == 0:
                z.add(el._id)
            else:
                e.append(el)
        data.models.elements = e
        for bl in data.models.beamlines:
            i = []
            for it in bl["items"]:
                if it not in z:
                    i.append(it)
            bl["items"] = i

    def __init_direction(self, data, from_class, to_class):
        self.from_class = sirepo.sim_data.get_class(from_class)
        self.to_class = sirepo.sim_data.get_class(to_class)
        self.vars = sirepo.template.import_module(self.from_class.sim_type()).code_var(
            data.models.rpnVariables
        )

    def __normalize_madx_beam(self, data):
        from sirepo.template import madx

        self.beam = copy.deepcopy(LatticeUtil.find_first_command(data, "beam"))
        cv = madx.code_var(data.models.rpnVariables)
        for f in ParticleEnergy.ENERGY_PRIORITY.madx:
            self.beam[f] = cv.eval_var_with_assert(self.beam[f])
        self.particle_energy = ParticleEnergy.compute_energy(
            self.from_class.sim_type(),
            self.beam.particle,
            self.beam.copy(),
        )
        self.beam.mass = ParticleEnergy.get_mass(
            self.from_class.sim_type(), self.beam.particle, self.beam
        )
        self.beam.charge = ParticleEnergy.get_charge(
            self.from_class.sim_type(), self.beam.particle, self.beam
        )
        beta_gamma = self.particle_energy.beta * self.particle_energy.gamma
        for dim in ("x", "y"):
            if (
                self.beam[f"e{dim}"]
                == self.from_class.schema().model.command_beam[f"e{dim}"][2]
                and self.beam[f"e{dim}n"]
            ):
                self.beam[f"e{dim}"] = (
                    self.vars.eval_var_with_assert(self.beam[f"e{dim}n"]) / beta_gamma
                )
        return data

    def _replace_var(self, data, name, value):
        v = self._find_var(data, name)
        if v:
            v.value = value
        else:
            data.models.rpnVariables.append(
                PKDict(
                    name=self._var_name(name),
                    value=value,
                )
            )

    def _var_name(self, name):
        return f"sr_{name}"
