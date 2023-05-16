# -*- coding: utf-8 -*-
"""Test pkcli.nersc_test

:copyright: Copyright (c) 2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
import pytest
import pykern.pkio
import pykern.pkunit
import sirepo.pkcli.nersc_test


def test_sequential():
    w = pykern.pkunit.work_dir()
    d = pykern.pkunit.data_dir()
    with pykern.pkio.save_chdir(w):
        sirepo.pkcli.nersc_test.sequential()
    pykern.pkunit.file_eq(
        expect_path=w.join("sirepo_run_dir").join("sequential_test.sh"),
        actual_path=d.join("expected_sequential_test.sh"),
    )
