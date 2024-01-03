# -*- coding: utf-8 -*-
"""test sirepo.csv

:copyright: Copyright (c) 2024 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""


def test_import():
    from pykern import pkunit, pkio
    from sirepo import csv

    for d in pkunit.case_dirs(group_prefix="conformance"):
        for f in pkio.sorted_glob("*.csv"):
            _ = csv.read_as_number_list(f)
        pass

    for d in pkunit.case_dirs(group_prefix="deviance"):
        for f in pkio.sorted_glob("*.csv"):
            with pkunit.pkexcept("invalid file"):
                _ = csv.read_as_number_list(f)
