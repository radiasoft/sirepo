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


_SIREPO_RUN_DIR_FILES = [
    "in.json",
    "nersc_sequential.log",
    "out.json",
    "parameters.py",
    "res_int_se.dat",
    "run.log",
    "sequential_test.sh",
    "sequential_test.sh.jinja",
]


def test_sequential():
    w = pykern.pkunit.work_dir()
    with pykern.pkio.save_chdir(w):
        pykern.pksubprocess.check_call_with_signals(
            ["sirepo", "nersc_test", "sequential"]
        )
        o = list(sorted([w.bestrelpath(f) for f in pykern.pkio.walk_tree(w)]))
    pykern.pkunit.pkeq(
        o,
        ["sirepo_run_dir/" + f for f in _SIREPO_RUN_DIR_FILES],
    )
