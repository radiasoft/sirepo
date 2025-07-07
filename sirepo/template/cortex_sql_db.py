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


def insert_material(parsed, qcall=None):
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


def list_materials():
    def _convert(row):
        return PKDict(
            material_id=row.material_id,
            created=int(row.created.timestamp()),
            material_name=row.material_name,
        )

    with _session(None) as s:
        return [_convert(r) for r in s.select("material").all()]


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


def _meta(path):
    f = "float 64"
    b = "bool"
    u = "str 8"
    return pykern.sql_db.Meta(
        uri=pykern.sql_db.sqlite_uri(path),
        schema=PKDict(
            material=PKDict(
                material_id="primary_id 1",
                uid=u + " index",
                created="datetime index",
                material_name="str 100 unique",
                availability_factor=f,
                density_g_cm3=f,
                is_atom_pct=b,
                is_bare_tile=b,
                is_homogenized_divertor=b,
                is_homogenized_hcpb=b,
                is_homogenized_wcll=b,
                is_neutron_source_dt=b,
                is_plasma_facing=b,
                neutron_wall_loading="str 32",
            ),
            material_component=PKDict(
                material_component_id="primary_id 2",
                material_id="primary_id",
                material_component_name="str 8",
                max_pct=f + " nullable",
                min_pct=f + " nullable",
                target_pct=f,
                unique=(("material_id", "material_component_name"),),
            ),
        ),
    )
