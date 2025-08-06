"""utilities for cortex

:copyright: Copyright (c) 2025 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from datetime import datetime
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
from sqlalchemy.schema import MetaData
import csv
import io
import openmc.data
import pykern.pkio
import pykern.pkjson
import pykern.sql_db
import re
import requests
import sqlalchemy

_CENTURY = 100.0 * 365 * 24 * 60 * 60


def gen_components():

    def _livechart_csv():
        r = requests.get(
            "https://nds.iaea.org/relnsd/v1/data?fields=ground_states&nuclides=all"
        )
        r.raise_for_status()
        return io.StringIO(r.text)

    def _parse():
        rv = PKDict(elements=set(), nuclides=set())
        first = True
        for r in csv.reader(_livechart_csv()):
            if not r:
                continue
            if first:
                first = False
                continue
            # num protons
            z = int(r[0])
            if z <= 0:
                continue
            symbol = r[2]
            rv.elements.add(symbol)
            # half_life or from stephen:
            # "Actually, there may be some short-lived lithium isotopes that may be embedded in 1st wall materials, so let’s include all the Lithiums"
            if r[12] != "STABLE" and symbol != "Li":
                # half_life_sec
                if r[16] in ("", "?") or float(r[16]) < _CENTURY:
                    continue
            rv.nuclides.add(r[2] + str(int(r[1]) + z))
        return rv

    def _to_str(components):
        rv = "_COMPONENTS = PKDict(\n"
        i = " " * 4
        j = i * 2
        for c in sorted(components.keys()):
            rv += i + c + "={\n"
            for n in sorted(components[c]):
                rv += f'{j}"{n}",\n'
            rv += i + "},\n"
        return rv + ")\n"

    return _to_str(_parse())


def export_tea(db_file):
    """Returns a python-compatible representation of all materials in the specified database."""
    # TODO(pjm): pass user and find database in lib_files?
    uri = pykern.sql_db.sqlite_uri(pykern.pkio.py_path(db_file))
    m = _populate_materials(_dump_sqlalchemy(uri))
    return f"MATERIALS = {_json_to_python(pykern.pkjson.dump_pretty(m))}"


def _convert_ao_to_wo(materials):

    def _ao_to_wo(ao):
        weight_sum = 0
        weight = PKDict()
        for e in ao:
            if re.search(r"\d", e):
                # Nuclide
                try:
                    w = openmc.data.atomic_mass(e)
                except KeyError as err:
                    raise ValueError(f"Unknown nuclide: {e}")
            else:
                # Element
                if e not in openmc.data.ATOMIC_NUMBER:
                    raise ValueError(f"Unknown element: {e}")
                # may raise ValueError: No naturally-occuring isotopes for element
                w = openmc.data.atomic_weight(e)
            weight[e] = ao[e].target_pct * w / openmc.data.AVOGADRO
            weight_sum += weight[e]

        wo = PKDict()
        for e in ao:
            wo[e] = PKDict(
                target_pct=100.0 * weight[e] / weight_sum,
                min_pct=None,
                max_pct=None,
            )
            if ao[e].max_pct is not None:
                if ao[e].min_pct is None:
                    wo[e].max_pct = wo[e].target_pct
                else:
                    wo[e].min_pct = ao[e].min_pct * wo[e].target_pct / ao[e].target_pct
                    wo[e].max_pct = ao[e].max_pct * wo[e].target_pct / ao[e].target_pct
        return wo

    for m in materials.values():
        if m.is_atom_pct:
            m.components = _ao_to_wo(m.components)
        del m["is_atom_pct"]


def _dump_sqlalchemy(uri):
    e = sqlalchemy.create_engine(uri)
    meta = MetaData()
    meta.reflect(bind=e)
    res = PKDict()
    with e.connect() as conn:
        for table in meta.sorted_tables:
            rows = [row._asdict() for row in conn.execute(sqlalchemy.select(table))]
            for row in rows:
                for col in row:
                    if isinstance(row[col], datetime):
                        row[col] = row[col].strftime("%Y-%m-%dT%H:%M:%SZ")
            res[table.name] = [PKDict(r) for r in rows]
    return res


def _find_by_id(rows, key, value):
    for r in rows:
        if r[key] == value:
            return r
    assert False


def _json_to_python(value):
    return re.sub(
        r"\bnull\b",
        "None",
        re.sub(r"\bfalse\b", "False", re.sub(r"\btrue\b", "True", value)),
    )


def _nest_values(dump, child_table, parent_table):
    for row in dump[child_table]:
        k = f"{parent_table}_id"
        p = _find_by_id(dump[parent_table], k, row[k])
        if child_table not in p:
            p[child_table] = []
        p[child_table].append(row)
        del row[k]
        k = f"{child_table}_id"
        if k in row:
            del row[k]
    del dump[child_table]


def _populate_materials(dump):
    for child, parent in [
        ["independent_variable_value", "independent_variable"],
        ["independent_variable", "material_property"],
        ["material_property_value", "material_property"],
        ["material_property", "material"],
        ["material_component", "material"],
    ]:
        _nest_values(dump, child, parent)

    _remap_to_name(
        dump.material, "material_component", "material_component_name", "components"
    )
    _remap_to_name(dump.material, "material_property", "property_name", "properties")

    for m in dump.material:
        for p in m.properties.values():
            if "independent_variable" in p:
                for v in p.independent_variable:
                    assert v.name not in p
                    p[v.name] = [x.value for x in v.independent_variable_value]
                del p["independent_variable"]
            if "material_property_value" in p:
                for v in p.material_property_value:
                    for k in v:
                        if k not in p:
                            p[k] = []
                        p[k].append(v[k])
                del p["material_property_value"]

    for m in dump.material:
        dump[m.material_name] = m
        del m["material_name"]
        del m["material_id"]
    del dump["material"]
    _convert_ao_to_wo(dump)
    return dump


def _remap_to_name(rows, source, name, target):
    for m in rows:
        m[target] = PKDict()
        if source in m:
            for p in m[source]:
                m[target][
                    p[name].capitalize() if target == "components" else p[name]
                ] = p
                del p[name]
            del m[source]
