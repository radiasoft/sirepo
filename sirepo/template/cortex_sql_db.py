"""Cortex db

:copyright: Copyright (c) 2025 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
import pykern.sql_db
import sqlalchemy

def add_material():
    pass

def _session(path):
    return pykern.sql_db.Meta(
        uri=pykern.sql_db.sqlite_uri(path),
        schema=PKDict(
            material_meta=PKDict(
                material_id="primary_id 1",
                material_name="str 100 primary_key",
                availability_factor="float",
                density_g_cm3="float",
                is_atom_pct="bool",
                is_bare_tile="bool",
                is_homogenized_divertor="bool",
                is_homogenized_hcpb="bool",
                is_homogenized_wcll="bool",
                is_neutron_source_dt="bool",
                is_plasma_facing="bool",
                neutron_wall_loading="float",
            ),
            material_component=PKDict(
                material_component_id="primary_id",
                material_id="primary_id",
                target_pct="float",
                min_pct="float nullable",
                max_pct="float nullable",
            ),
        ),
    ).session()
