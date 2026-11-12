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
            if "multi" in d.basename:
                p = material_xlsx.parse(d.join("input.xlsx"))
                x = p.errors or p.materials
            else:
                p = material_xlsx.Parser(d.join("input.xlsx"))
                x = p.errors or p.result
            pkjson.dump_pretty(x, filename=d.join(f"out.json"))


def test_multi_template():
    """The template for multiple materials must parse"""
    from pykern import pkunit
    from sirepo.sim_api.cortex import material_xlsx
    import sirepo.resource

    p = material_xlsx.parse(
        sirepo.resource.file_path(
            "template", "cortex", "lib", "materials_multi_input.xlsx"
        ),
    )
    pkunit.pkeq([], p.errors)
    pkunit.pkeq(
        [
            "Fe 9Cr 1W 0.2V",
            "Fe 9Cr 1.5W 0.25V",
            "Fe 11Cr 1W 0.3V 0.1Ta",
            "Fe 12Cr 2W 0.2V",
            "W 1Ta",
        ],
        [m.material_name for m in p.materials],
    )
