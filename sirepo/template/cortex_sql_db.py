"""Cortex db

:copyright: Copyright (c) 2025 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
import contextlib
import pykern.sql_db
import sqlalchemy
import sirepo.sim_data
import pykern.pkio

_BASE = "materials.sqlite3"


def insert_material(parsed, qcall=None):
    def _values(cols, vals):
        return PKDict((c, vals[c]) for c in cols if c in vals)

    with _session(qcall=qcall) as s:
        i = s.insert("material", _values(s.t.material.columns.keys(), parsed)).material_id
        for v in parsed.components:
            i = s.insert("material", _values(s.t.material.columns.keys(), parsed)).material_id




@contextlib.contextmanager
def _session(qcall):
    s = sirepo.sim_data.get_class("cortex")
    if w := (not (p := s.lib_file_exists(_BASE, qcall=qcall))):
        p = pykern.pkio.py_path(_BASE)

    with _meta(p).session() as rv:
        yield rv
    if w or s.hack_for_cortex_is_agent_side():
        s.lib_file_write(_BASE, p, qcall=qcall)


def _meta(path):
    f = "float 64"
    return pykern.sql_db.Meta(
        uri=pykern.sql_db.sqlite_uri(path),
        schema=PKDict(
            material=PKDict(
                material_id="primary_id 1",
                material_name="str 100 unique",
                availability_factor=f,
                density_g_cm3=f,
                is_atom_pct="bool",
                is_bare_tile="bool",
                is_homogenized_divertor="bool",
                is_homogenized_hcpb="bool",
                is_homogenized_wcll="bool",
                is_neutron_source_dt="bool",
                is_plasma_facing="bool",
                neutron_wall_loading="str 32",
            ),
            material_component=PKDict(
                material_component_id="primary_id 2",
                material_id="primary_id",
                material_component_name="str 8 unique",
                max_pct=f + " nullable",
                min_pct=f + " nullable",
                target_pct=f,
            ),
        ),
    )
