"""test import of the sim summary zip

:copyright: Copyright (c) 2026 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

_MATERIAL_ID = 1001

_REPORT = "hcpbSlabAnimation"


def test_all():
    from pykern import pkcompat, pkio, pkjson, pkunit
    from pykern.pkcollections import PKDict
    from sirepo import srunit
    from sirepo.sim_api.cortex import material_db
    import datetime
    import sirepo.sim_api.cortex
    import sirepo.sim_data
    import sirepo.simulation_db
    import sirepo.template.cortex
    from sirepo.template import template_common
    import subprocess
    import zipfile

    def _sqlite3(name, uid):
        f = pkio.read_text(pkunit.data_dir().join(f"{name}.sql"))
        if uid:
            f = f.replace("UNIT_TEST_UID", uid)
        subprocess.run(
            ["sqlite3", str(material_db._path())],
            check=True,
            input=pkcompat.to_bytes(f),
        )

    def _write_zip(qcall, file_material_id=_MATERIAL_ID):
        z = pkunit.work_dir().join("summary.zip")
        with zipfile.ZipFile(str(z), "w") as f:
            f.writestr("dpa_all.png", b"png")
            f.writestr("neutronics.hdf5", b"hdf5")
            f.writestr(
                _SIM_DATA.SUMMARY_JSON,
                pkjson.dump_str(
                    PKDict(
                        material_id=_MATERIAL_ID,
                        model=_REPORT,
                        version="1.03",
                        completed=datetime.datetime.now(datetime.timezone.utc),
                        values=[],
                        plots=[
                            PKDict(
                                material_id=_MATERIAL_ID,
                                model=_REPORT,
                                stat="dpa_all",
                                title="DPA",
                                xlabel="x",
                                ylabel="y",
                                plot_type="linear",
                                csv="x,y\n1,2\n",
                            ),
                        ],
                    ),
                ),
            )
        _SIM_DATA.lib_file_write(
            _SIM_DATA.summary_file_from_parts(_REPORT, file_material_id),
            z,
            qcall=qcall,
        )

    _SIM_DATA = sirepo.sim_data.get_class("cortex")
    srunit.setup_srdb_root()
    _sqlite3("schema", None)
    with srunit.quest_start(want_user=True) as qcall:
        with pkunit.save_chdir_work(want_empty=False):
            uid = qcall.auth.logged_in_user()
            _sqlite3("data", uid)
            # sorts first, but doesn't stop the import of the summary
            _SIM_DATA.lib_file_write("a-summary.zip", b"x", qcall=qcall)
            _write_zip(qcall)
            # one summary is imported per call
            pkunit.pkeq(True, sirepo.sim_api.cortex.check_for_sim_summary(qcall, uid))
            pkunit.pkeq(False, sirepo.sim_api.cortex.check_for_sim_summary(qcall, uid))
            b = _SIM_DATA.lib_file_write_path("a-summary.zip", qcall=qcall)
            pkunit.pkok(not b.exists(), "{} was not moved", b)
            pkunit.pkok(b.new(ext="zip.failed").exists(), "{}.failed missing", b)
            d = material_db.cortexdb_path(_MATERIAL_ID, _REPORT)
            pkunit.pkeq(b"png", d.join("dpa_all.png").read_binary())
            pkunit.pkeq(b"hdf5", d.join("neutronics.hdf5").read_binary())
            pkunit.pkeq(
                "x,y\n1,2\n",
                pkio.read_text(
                    material_db.plot_csv_path(_MATERIAL_ID, _REPORT, "dpa_all")
                ),
            )
            pkunit.pkeq(
                ["DPA"],
                [
                    p.title
                    for p in material_db.load_summary(_MATERIAL_ID, False, uid).plots
                ],
            )
            # the zip written by the sim imports
            r = pkio.mkdir_parent(pkunit.work_dir().join("run_dir"))
            pkjson.dump_pretty(
                PKDict(models=PKDict(material=PKDict(material_id=_MATERIAL_ID))),
                filename=r.join(template_common.INPUT_BASE_NAME),
            )
            pkjson.dump_pretty(
                PKDict(
                    plots=[PKDict(x=[1.0, 2.0], y=[3.0, 4.0], label="")],
                    xlabel="x",
                    ylabel="y",
                    type="linear",
                ),
                filename=r.join("dpa_OB_1_b6.png.json"),
            )
            r.join("dpa_OB_1_b6.png").write_binary(b"png2")
            for n in sirepo.template.cortex.STATEPOINTS:
                r.join(f"{n}.hdf5").write_binary(n.encode())
            # not in an agent, so lib_file_write needs the user
            sirepo.simulation_db._cfg.logged_in_user = uid
            sirepo.template.cortex._save_summary_to_database(
                r, _REPORT, ["dpa_OB_1_b6"]
            )
            pkunit.pkeq(True, sirepo.sim_api.cortex.check_for_sim_summary(qcall, uid))
            pkunit.pkeq(b"png2", d.join("dpa_OB_1_b6.png").read_binary())
            pkunit.pkeq(b"depletion", d.join("depletion.hdf5").read_binary())
            # the file name can't point at another material than the json
            _write_zip(qcall, file_material_id=2001)
            with pkunit.pkexcept("does not match"):
                sirepo.sim_api.cortex.check_for_sim_summary(qcall, uid)
            pkunit.pkok(
                not material_db.cortexdb_path(2001, _REPORT).exists(),
                "files written for the material of the file name",
            )
            # the list has the summary values of the model asked for
            for m, v in (("hcpbSlabAnimation", 1.5), ("wcllSlabAnimation", 2.5)):
                material_db.update_sim_summary(
                    PKDict(
                        material_id=_MATERIAL_ID,
                        model=m,
                        version="1.03",
                        completed=datetime.datetime.now(datetime.timezone.utc),
                        values=[
                            PKDict(layer=l, dpa_fpy=v) for l in ("Armor", "First Wall")
                        ],
                        plots=[],
                    ),
                    uid,
                )
            for m, v in (
                (None, 1.5),
                ("hcpbSlabAnimation", 1.5),
                ("wcllSlabAnimation", 2.5),
                ("hcllSlabAnimation", None),
            ):
                pkunit.pkeq(
                    v,
                    [
                        r.get("dpa_fpy")
                        for r in (
                            material_db.list_materials(uid, m)
                            if m
                            else material_db.list_materials(uid)
                        )
                        if r.material_id == _MATERIAL_ID
                    ][0],
                )
            with pkunit.pkexcept("BadRequest"):
                material_db.list_materials(uid, "notASlabAnimation")
            # a different user can't import a summary for the material
            _write_zip(qcall)
            with pkunit.pkexcept("NoRows"):
                sirepo.sim_api.cortex.check_for_sim_summary(qcall, "other-uid")
