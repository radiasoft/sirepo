# -*- coding: utf-8 -*-
"""ImpactT parser.

:copyright: Copyright (c) 2024 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from impact.parsers import parse_header, ix_lattice, parse_lattice
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
import re
import sirepo.sim_data


class ImpactTParser(object):

    _IGNORE_FIELDS = set(
        ["Npcol", "Nprow", "Nbunch", "Flagmap", "Flagbc", "Rstartflg", "Flagsbstp"]
    )
    _IGNORE_MODELS = set(["COMMENT"])
    _IGNORE_MODEL_FIELDS = set(["description", "original", "type", "s", "zedge"])

    def parse_file(self, lattice_text):
        from sirepo import simulation_db

        self.sim_data = sirepo.sim_data.get_class("impactt")
        self.schema = self.sim_data.schema()
        self.data = simulation_db.default_data(self.sim_data.sim_type())
        self.next_id = 0
        return self._import_impactt(self._parse_impactt(lattice_text))

    def _elements_and_positions(self, lattice):
        elements = []
        positions = []

        for el in lattice:
            n = el["type"].upper()
            if n in self._IGNORE_MODELS:
                continue
            if n not in self.schema.model:
                pkdlog("unhandled model: {}", el["type"])
                continue
            m = self.schema.model[n]
            element = self.sim_data.model_defaults(n).pkupdate(
                type=n,
            )
            positions.append(el["zedge"] if "zedge" in el else el["s"])
            for k, v in el.items():
                f = "l" if k == "L" else k
                if f in m:
                    if self._is_enum(n, f):
                        element[f] = str(v)
                    else:
                        element[f] = v
                elif k in self._IGNORE_MODEL_FIELDS:
                    continue
                else:
                    pkdlog("unhandled model field {}: {} = {}", n, k, v)
            elements.append(element)
        return elements, positions

    def _import_elements(self, lattice):
        elements, positions = self._elements_and_positions(lattice)
        for e in sorted(zip(positions, elements)):
            self.data.models.beamlines[0].positions.append(
                PKDict(
                    elemedge=e[0],
                )
            )
            e[1]._id = self._next_id()
            self.data.models.elements.append(e[1])
            self.data.models.beamlines[0]["items"].append(e[1]._id)
        self.data.models.elements = sorted(
            self.data.models.elements, key=lambda e: (e.type, e.name.lower())
        )

    def _import_header(self, header):
        for k, v in header.items():
            if k in self._IGNORE_FIELDS:
                continue
            matched = False
            for m in ("beam", "distribution", "simulationSettings"):
                f = re.sub(r"\(.*\)", "", k)
                if f in self.data.models[m]:
                    if self._is_enum(m, f):
                        self.data.models[m][f] = str(v)
                    else:
                        self.data.models[m][f] = v
                    matched = True
                    break
            if not matched:
                pkdlog("unhandled header value {}: {}", k, v)

    def _import_impactt(self, parsed):
        self.data.models.beamlines = [
            self.sim_data.model_defaults("beamline").pkupdate(
                id=self._next_id(),
                items=[],
                positions=[],
                name="BL1",
            )
        ]
        self._import_header(parsed.header)
        self._import_elements(parsed.lattice)
        return self.data

    def _is_enum(self, model_name, field):
        return self.schema.model[model_name][field][1] in self.schema.enum

    def _next_id(self):
        self.next_id += 1
        return self.next_id

    def _parse_impactt(self, lattice_text):
        lines = lattice_text.split("\n")
        return PKDict(
            header=parse_header(lines),
            lattice=parse_lattice(lines[ix_lattice(lines) :]),
        )
