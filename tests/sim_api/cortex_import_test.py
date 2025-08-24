"""test cortex import

:copyright: Copyright (c) 2025 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

_INPUT = "input.xlsx"

_SQL = """select material_name, availability_factor from material order by material_name;
select material_component_name, target_pct from material_component order by material_component_name;"""


def test_cases():
    from sirepo import srunit

    def _out_content(import_rv):
        from pykern import pkdebug, pkjson, pkunit

        if "error" in import_rv:
            return import_rv
        pkunit.pkeq(["imported_data"], list(import_rv))
        i = import_rv.imported_data
        return PKDict(
            models_keys=sorted(i.models),
            simulation_name=i.models.simulation.name,
        )

    def _tables_csv(path):
        import subprocess
        from pykern import pkio

        # _import_file writes the db locally
        pkio.write_text(
            "tables.csv",
            subprocess.check_output(["sqlite3", path, _SQL], text=True),
        )

    with srunit.quest_start(want_global_user=True) as qcall:
        from pykern import pkdebug, pkjson, pkunit
        from pykern.pkcollections import PKDict
        from sirepo.template import cortex, cortex_sql_db
        from sirepo import sim_data

        for d in pkunit.case_dirs():
            sim_data.get_class("cortex").lib_file_write(
                _INPUT, d.join(_INPUT), qcall=qcall
            )
            pkjson.dump_pretty(
                _out_content(
                    cortex.stateful_compute_import_file(
                        PKDict(args=PKDict(lib_file=_INPUT)),
                    )
                ),
                filename=d.join(f"out.json"),
            )
            _tables_csv(cortex_sql_db._BASE)
