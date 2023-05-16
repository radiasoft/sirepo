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
            ["sirepo", "nersc_test", "sequential"]
        )
        o = list(sorted([w.bestrelpath(f) for f in pykern.pkio.walk_tree(w)]))
    pykern.pkunit.pkeq(
        o,
        [
            "sirepo_run_dir/in.json",
            "sirepo_run_dir/nersc_sequential.log",
            "sirepo_run_dir/out.json",
            "sirepo_run_dir/parameters.py",
            "sirepo_run_dir/res_int_se.dat",
            "sirepo_run_dir/run.log",
            "sirepo_run_dir/sequential_test.sh",
            "sirepo_run_dir/sequential_test.sh.jinja",
        ],
    )
    pykern.pkunit.file_eq(
        expect_path=w.join("sirepo_run_dir").join("sequential_test.sh"),
        actual_path=pykern.pkunit.data_dir().join("expected_sequential_test.sh"),
    )
