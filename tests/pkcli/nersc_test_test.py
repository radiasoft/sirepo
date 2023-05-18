# -*- coding: utf-8 -*-
"""Test pkcli.nersc_test

:copyright: Copyright (c) 2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
import pytest
import pykern.pkio
import pykern.pkunit
import sirepo.pkcli.nersc_test
import pykern.pksubprocess


def test_sequential():
    w = pykern.pkunit.work_dir()
    with pykern.pkio.save_chdir(w):
        pykern.pksubprocess.check_call_with_signals(
            ["sirepo", "nersc_test", "sequential"],
            output="result.log",
        )
    pykern.pkunit.pkeq(
        pykern.pkio.read_text(w.join("result.log")).strip(),
        "nersc_test.sequential PASS",
    )
