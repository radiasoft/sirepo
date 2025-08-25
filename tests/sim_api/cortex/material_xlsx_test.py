"""test cortex xlsx parser

:copyright: Copyright (c) 2025 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""


def test_cases():
    from sirepo import srunit

    with srunit.quest_start(want_user=True) as qcall:
        from pykern import pkdebug, pkjson, pkunit
        from sirepo.sim_api.cortex import material_xlsx

        for d in pkunit.case_dirs():
            p = material_xlsx.Parser(d.join("input.xlsx"))
            pkjson.dump_pretty(
                getattr(p, "errors" if p.errors else "result"),
                filename=d.join(f"out.json"),
            )
