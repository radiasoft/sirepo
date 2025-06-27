"""test cortex import

:copyright: Copyright (c) 2025 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""


def test_cases():
    from sirepo import srunit

    with srunit.quest_start(want_user=True) as qcall:
        from pykern import pkdebug, pkjson, pkunit
        from pykern.pkcollections import PKDict
        from sirepo.template import cortex

        for d in pkunit.case_dirs():
            pkjson.dump_pretty(
                cortex._import_file(
                    PKDict().pknested_set(
                        "args.import_file_arguments.file_as_bytes",
                        d.join("input.xlsx").read_binary(),
                    )
                ),
                filename=d.join(f"out.json"),
            )
