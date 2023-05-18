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


class _SequentialTest:
    def __init__(self):
        self._CMD_BASIC = ["sirepo", "nersc_test", "sequential"]
        self._work_dir = pykern.pkunit.work_dir()
        self._data_dir = pykern.pkunit.data_dir()
        self._output = "result.log"

    def test(self):
        self._success_case()
        self._failure_case()

    def _failure_case(self):
        self._exec_cmd(
            [
                *self._CMD_BASIC,
                f"job_cmd_in_path={self._data_dir.join('failure_in.json.jinja')}",
            ]
        )
        pykern.pkunit.pkeq(
            pykern.pkio.read_text(self._work_dir.join("result.log")).split("\n")[0],
            "nersc_test sequential fail: error=unexpected result state=error",
        )

    def _success_case(self):
        self._exec_cmd(self._CMD_BASIC)
        pykern.pkunit.pkeq(
            pykern.pkio.read_text(self._work_dir.join("result.log")).strip(),
            "nersc_test.sequential PASS",
        )

    def _exec_cmd(self, cmd):
        with pykern.pkio.save_chdir(self._work_dir):
            pykern.pksubprocess.check_call_with_signals(
                cmd,
                output=self._output,
            )


def test_sequential():
    _SequentialTest().test()
