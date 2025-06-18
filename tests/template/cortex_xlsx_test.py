"""test cortex xlsx parser

:copyright: Copyright (c) 2025 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""


def test_cases():
    from pykern import pkdebug, pkjson, pkunit
    from sirepo.template import cortex_xlsx

    for d in pkunit.case_dirs():
        pkjson.dump_pretty(
            cortex_xlsx.Parser(d.join("input.xlsx")).result,
            filename=d.join("result.json"),
        )
