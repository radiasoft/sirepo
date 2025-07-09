"""cortex db test

:copyright: Copyright (c) 2025 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""


def test_cases():
    from sirepo import srunit

    with srunit.quest_start(want_user=True) as qcall:
        from pykern import pkdebug, pkunit, pkio, pkjson
        from pykern.pkcollections import PKDict
        from sirepo import simulation_db
        from sirepo.template import cortex

        # from sirepo.template import cortex_xlsx
        import subprocess

        simulation_db._cfg.logged_in_user = qcall.auth.logged_in_user()
        db = simulation_db.simulation_lib_dir("cortex", qcall).join("cortex.sqlite3")

        for d in pkunit.case_dirs():
            pkio.unchecked_remove(db)
            subprocess.run(
                [
                    "sqlite3",
                    str(db),
                ],
                check=True,
                input=d.join("in.sql").read_binary(),
            )
            pkjson.dump_pretty(
                cortex.stateful_compute_cortex_db(
                    PKDict(
                        args=PKDict(
                            api_name="list_materials",
                        ),
                    )
                ),
                filename="out.json",
            )
