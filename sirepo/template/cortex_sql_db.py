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
import sirepo.sim_data
import pykern.pkio

_BASE = "cortex.sqlite3"


class Error(RuntimeError):
    pass


def delete_material(material_id):
    """Cascade delete all rows for a material"""

    def _delete(session, table_name, field, value):
        session.delete(table_name, PKDict({field: value}))

    def _select_id(session, table_name, field, value):
        return [
            v[f"{table_name}_id"]
            for v in s.select(table_name, PKDict({field: value})).all()
        ]

    with _session(None) as s:
        for mp in _select_id(s, "material_property", "material_id", material_id):
            for mpv in _select_id(
                s, "material_property_value", "material_property_id", mp
            ):
                _delete(
                    s, "independent_variable_value", "material_property_value_id", mpv
                )
            _delete(s, "material_property_value", "material_property_id", mp)
            _delete(s, "independent_variable", "material_property_id", mp)
        for t in ("material_property", "material_component", "material"):
            _delete(s, t, "material_id", material_id)


def insert_material(parsed, qcall=None):
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

    with _session(qcall=qcall) as s:
        try:
            i = s.insert(
                "material",
                # TODO(robnagler) need uid. we will have to have a db server of some sort
                # it will have to validate incoming uid.
                # sim_db_file is a model that could be used for writing to
                # the database, because it validates the uid.
                # sim_db_file should have a multithreaded worker queue. the serialization
                # is already there.
                _values(s.t.material.columns.keys(), parsed).pkupdate(uid="TODO RJN"),
            ).material_id
        except sqlalchemy.exc.IntegrityError as e:
            if "unique" in str(e).lower():
                # Needs to raise to signal to the session to rollback
                raise Error("material name already exists")
            raise
        for v in parsed.components.values():
            s.insert(
                "material_component",
                _values(s.t.material_component.columns.keys(), v).pkupdate(
                    material_id=i
                ),
            )
        for n in parsed.properties:
            _insert_property(s, n, parsed.properties[n].pkupdate(material_id=i))


def list_materials():
    def _convert(row):
        return PKDict(
            material_id=row.material_id,
            created=int(row.created.timestamp()),
            material_name=row.material_name,
        )

    with _session(None) as s:
        return [_convert(r) for r in s.select("material").all()]


def _meta(path):
    f = "float 64"

    def _optional(v):
        return f"{v} nullable"

    return pykern.sql_db.Meta(
        uri=pykern.sql_db.sqlite_uri(path),
        schema=PKDict(
            material=PKDict(
                material_id="primary_id 1",
                uid="str 8 index",
                created="datetime index",
                material_name="str 100 unique",
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


@contextlib.contextmanager
def _session(qcall):
    s = sirepo.sim_data.get_class("cortex")
    p = pykern.pkio.py_path(_BASE)
    if s.lib_file_exists(_BASE, qcall=qcall):
        p.write_binary(s.lib_file_read_binary(_BASE, qcall=qcall))
    try:
        with _meta(p).session() as rv:
            yield rv
    except:
        raise
    else:
        s.lib_file_write(_BASE, p, qcall=qcall)
