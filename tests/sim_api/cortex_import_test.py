"""test cortex import

:copyright: Copyright (c) 2025 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

_INPUT = "input.xlsx"

_SQL = """select material_name, availability_factor from material order by material_name;
select material_component_name, target_pct from material_component order by material_component_name;"""


def test_all(fc):
    from pykern import pkdebug, pkjson, pkunit, pkio
    from pykern.pkcollections import PKDict
    from sirepo.sim_api.cortex import material_db
    import subprocess

    db_path = material_db._path()
    for d in pkunit.case_dirs():
        r = fc.sr_post(
            "cortexDb",
            data=PKDict(op_name="insert_material", op_args=PKDict()),
            file_handle=d.join(_INPUT).open("rb"),
        )
        pkjson.dump_pretty(r, filename="insert.json")
        if "error" in r:
            continue
        pkio.write_text(
            "tables.csv",
            subprocess.check_output(["sqlite3", "-csv", db_path, _SQL], text=True),
        )
        pkdebug.pkdp(r)
        pkjson.dump_pretty(
            fc.sr_post(
                "cortexDb",
                data=PKDict(
                    op_name="material_detail",
                    op_args=PKDict(material_id=r.op_result.material_id),
                ),
            ).op_result,
            filename="detail.json",
        )
