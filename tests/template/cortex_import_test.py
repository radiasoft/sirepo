"""test cortex import

:copyright: Copyright (c) 2025 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

_INPUT = "input.xlsx"


def test_cases():
    from sirepo import srunit

    with srunit.quest_start(want_user=True) as qcall:
        from pykern import pkdebug, pkjson, pkunit
        from pykern.pkcollections import PKDict
        from sirepo.template import cortex
        from sirepo import sim_data

        for d in pkunit.case_dirs():
            sim_data.get_class("cortex").lib_file_write(
                _INPUT, d.join(_INPUT), qcall=qcall
            )
            pkjson.dump_pretty(
                cortex._import_file(PKDict(args=PKDict(lib_file=_INPUT)), qcall=qcall),
                filename=d.join(f"out.json"),
            )
