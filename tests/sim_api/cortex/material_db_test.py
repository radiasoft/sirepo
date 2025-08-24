"""cortex db test

:copyright: Copyright (c) 2025 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""


def test_cases():
    from sirepo import srunit

    with srunit.quest_start(want_user=True) as qcall:
        from pykern import pkcompat, pkdebug, pkunit, pkio, pkjson
        from pykern.pkcollections import PKDict
        from sirepo.pkcli import cortex
        from sirepo.sim_api.cortex import material_db
        import re
        import subprocess

        def _dump_list(uid, path):
            pkjson.dump_pretty(material_db.list_materials(uid=uid), filename=path)

        def _sql(dirpath, uid):
            return pkcompat.to_bytes(
                pkio.read_text(dirpath.join("in.sql")).replace("UNIT_TEST_UID", uid),
            )

        material_db.init_from_api()
        db_path = str(material_db._path())
        uid = qcall.auth.logged_in_user()
        for d in pkunit.case_dirs():
            pkio.unchecked_remove(db_path)
            subprocess.run(["sqlite3", db_path], check=True, input=_sql(d, uid))
            _dump_list(uid, "out.json")
            v = cortex.export_tea(db_path)
            pkio.write_text("out.py", re.sub(r"# Generated on .*\n", "", v))
            material_db.delete_material(material_id=1001, uid=uid)
            _dump_list(uid, "out2.json")
