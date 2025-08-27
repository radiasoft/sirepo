"""cortex db test

:copyright: Copyright (c) 2025 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""


def test_all():
    from pykern import pkcompat, pkdebug, pkunit, pkio, pkjson
    from pykern.pkcollections import PKDict
    from sirepo import srunit
    import re
    import subprocess
    from sirepo.sim_api.cortex import material_db

    srunit.setup_srdb_root()
    db_path = str(material_db._path())

    def _data(base):
        return pkunit.data_dir().join(base)

    def _sqlite3(name, uid):
        nonlocal db_path

        f = pkio.read_text(_data(f"{name}.sql"))
        if uid:
            f = f.replace("UNIT_TEST_UID", uid)
        subprocess.run(["sqlite3", db_path], check=True, input=pkcompat.to_bytes(f))

    _sqlite3("schema", None)
    with srunit.quest_start(want_user=True) as qcall:
        with pkunit.save_chdir_work(want_empty=False):
            from sirepo.pkcli import cortex

            uid = qcall.auth.logged_in_user()
            _sqlite3("data", uid)
            pkunit.file_eq("out.json", material_db.list_materials(uid=uid))
            pkio.write_text(
                "tea.py",
                re.sub(r"# Generated on .*\n", "", cortex.export_tea(db_path)),
            )
            pkunit.file_eq(_data("tea.py"), actual_path="tea.py")
            pkunit.file_eq(
                "detail.json",
                material_db.material_detail(material_id=1001, uid=uid),
            )
            material_db.delete_material(material_id=1001, uid=uid)
            with pkunit.pkexcept("not found"):
                material_db.material_detail(material_id=1001, uid=uid)
