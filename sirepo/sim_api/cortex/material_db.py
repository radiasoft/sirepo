"""Cortex db

:copyright: Copyright (c) 2025 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
import contextlib
import pykern.sql_db
import sqlalchemy
import sqlalchemy.exc
import sirepo.srdb

_BASE = "cortex_material.sqlite3"

_meta = None


class Error(RuntimeError):
    pass


def delete_material(material_id, uid):
    """Cascade delete all rows for a material"""

    def _delete(session, table_name, **where):
        session.delete(table_name, _where(table_name, where))

    def _select_id(session, table_name, **where):
        return [
            v[f"{table_name}_id"]
            for v in session.select(table_name, _where(table_name, where)).all()
        ]

    def _where(table_name, fields):
        rv = PKDict(fields)
        if table_name == "material":
            rv.uid = uid
        return rv

    with _session() as s:
        if len(_select_id(s, "material", material_id=material_id)) < 1:
            # Possible with two simultaneous deletes, but highly unlikely
            # TODO(robnagler) assert?
            pkdlog("unexpected not found material_id={} uid={}", material_id, uid)
            return False
        for p in _select_id(s, "material_property", material_id=material_id):
            for v in _select_id(s, "material_property_value", material_property_id=p):
                _delete(s, "independent_variable_value", material_property_value_id=v)
            _delete(s, "material_property_value", material_property_id=p)
            _delete(s, "independent_variable", material_property_id=p)
        for t in ("material_property", "material_component", "material"):
            _delete(s, t, material_id=material_id)
    return True


def init_from_api():
    global _meta

    def _optional(v):
        return f"{v} nullable"

    f = "float 64"
    _meta = pykern.sql_db.Meta(
        uri=pykern.sql_db.sqlite_uri(_path()),
        schema=PKDict(
            material=PKDict(
                material_id="primary_id 1",
                uid="str 8 index",
                created="datetime index",
                material_name="str 100",
                availability_factor=_optional(f),
                density_g_cm3=f,
                is_atom_pct="bool",
                is_bare_tile=_optional("bool"),
                is_homogenized_divertor=_optional("bool"),
                is_homogenized_hcpb=_optional("bool"),
                is_homogenized_wcll=_optional("bool"),
                is_neutron_source_dt=_optional("bool"),
                is_plasma_facing="bool",
                neutron_wall_loading=_optional("str 32"),
                structure=_optional("str 100"),
                microstructure=_optional("str 500"),
                processing_steps=_optional("str 500"),
                unique=(("uid", "material_name"),),
            ),
            material_component=PKDict(
                material_component_id="primary_id 2",
                material_id="primary_id",
                material_component_name="str 8",
                max_pct=_optional(f),
                min_pct=_optional(f),
                target_pct=f,
                unique=(("material_id", "material_component_name"),),
            ),
            material_property=PKDict(
                material_property_id="primary_id 3",
                material_id="primary_id",
                property_name="str 100",
                property_unit="str 32",
                doi_or_url=_optional("str 500"),
                source=_optional("str 32"),
                pointer=_optional("str 32"),
                comments=_optional("str 5000"),
                unique=(("material_id", "property_name"),),
            ),
            material_property_value=PKDict(
                material_property_value_id="primary_id 4",
                material_property_id="primary_id",
                value=f,
                uncertainty=_optional(f),
                temperature_k=f,
                neutron_fluence_1_cm2=f,
            ),
            independent_variable=PKDict(
                independent_variable_id="primary_id 5",
                material_property_id="primary_id",
                name="str 100",
                unique=(("material_property_id", "name"),),
            ),
            independent_variable_value=PKDict(
                independent_variable_id="primary_id primary_key",
                material_property_value_id="primary_id primary_key",
                value=f,
            ),
        ),
    )


def insert_material(parsed, uid):
    def _insert_property(session, name, values):
        vals = values.pop("vals")
        ivars = values.pop("independent_variables", PKDict())
        prop_id = session.insert(
            "material_property",
            property_name=name,
            **values,
        ).material_property_id
        ivar_ids = {
            name: session.insert(
                "independent_variable",
                material_property_id=prop_id,
                name=name,
            ).independent_variable_id
            for name in ivars
        }
        for idx, val in enumerate(vals):
            val_id = session.insert(
                "material_property_value",
                material_property_id=prop_id,
                **val,
            ).material_property_value_id
            for name, values_list in ivars.items():
                session.insert(
                    "independent_variable_value",
                    independent_variable_id=ivar_ids[name],
                    material_property_value_id=val_id,
                    value=values_list[idx],
                )

    def _values(cols, vals):
        return PKDict((c, vals[c]) for c in cols if c in vals)

    with _session() as s:
        try:
            rv = s.insert(
                "material",
                _values(s.t.material.columns.keys(), parsed).pkupdate(uid=uid),
            )
        except sqlalchemy.exc.IntegrityError as e:
            if "unique" in str(e).lower():
                # Needs to raise to signal to the session to rollback
                raise Error(f"material name={parsed.material_name} already exists")
            raise
        for v in parsed.components.values():
            s.insert(
                "material_component",
                _values(s.t.material_component.columns.keys(), v).pkupdate(
                    material_id=rv.material_id
                ),
            )
        for n in parsed.properties:
            _insert_property(
                s, n, parsed.properties[n].pkupdate(material_id=rv.material_id)
            )
        return PKDict((k, rv[k]) for k in ("material_id", "material_name"))


def list_materials(uid):
    def _convert(row):
        return PKDict(
            material_id=row.material_id,
            created=int(row.created.timestamp()),
            material_name=row.material_name,
        )

    with _session() as s:
        return [_convert(r) for r in s.select("material", where=PKDict(uid=uid)).all()]


def material_detail(material_id, uid):
    def _record(session, table_name, row):
        return PKDict(
            zip(
                [c.name for c in session.meta.tables[table_name].columns],
                row,
            )
        )

    def _records(session, table_name, record, field):
        return [
            _record(s, table_name, r)
            for r in session.select(table_name, where={field: record[field]}).all()
        ]

    with _session() as s:
        rv = _record(
            s,
            "material",
            s.select_one("material", where=PKDict(material_id=material_id, uid=uid)),
        )
        # Makes testing hard, and don't need to return
        rv.pkdel("uid")
        rv.components = _records(s, "material_component", rv, "material_id")
        rv.properties = _records(s, "material_property", rv, "material_id")
        for p in rv.properties:
            p.vals = _records(s, "material_property_value", p, "material_property_id")
            ivs = PKDict(
                [
                    (r.independent_variable_id, r.name)
                    for r in _records(
                        s, "independent_variable", p, "material_property_id"
                    )
                ]
            )
            for mpv in p.vals:
                for iv in _records(
                    s, "independent_variable_value", mpv, "material_property_value_id"
                ):
                    mpv[ivs[iv.independent_variable_id]] = iv.value
        return rv


def _path():
    return sirepo.srdb.root().join(_BASE)


def _session():
    return _meta.session()
