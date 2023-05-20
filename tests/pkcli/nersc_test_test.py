# -*- coding: utf-8 -*-
"""Test pkcli.nersc_test

:copyright: Copyright (c) 2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
import pytest


class _SequentialTest:
    def __init__(self):
        from pykern import pkunit

        self._work_dir = pkunit.work_dir()
        self._data_dir = pkunit.data_dir()
        self._output = "result.log"

    def conformance(self):
        self._test(
            "nersc_test.sequential PASS",
            lambda s: s.strip(),
        )

    def deviance(self):
        self._test(
            "nersc_test sequential fail: error=unexpected result state=error",
            lambda s: s.split("\n")[0],
            cmd_arg=f"job_cmd_in_path={self._data_dir.join('failure_in.json.jinja')}",
        )

    def _test(self, expect, out_fn, cmd_arg=None):
        from pykern import pkio
        from pykern import pkunit

        self._exec_cmd(cmd_arg)
        pkunit.pkeq(
            out_fn(pkio.read_text(self._work_dir.join(self._output))),
            expect,
        )

    def _cmd(self, cmd_arg=None):
        c = ["sirepo", "nersc_test", "sequential"]
        if cmd_arg:
            c.append(cmd_arg)
        return c

    def _exec_cmd(self, cmd_arg=None):
        from pykern import pksubprocess
        from pykern import pkio

        with pkio.save_chdir(self._work_dir):
            pksubprocess.check_call_with_signals(
                self._cmd(cmd_arg),
                output=self._output,
            )


def test_conformance():
    _SequentialTest().conformance()


def test_deviance():
    _SequentialTest().deviance()
