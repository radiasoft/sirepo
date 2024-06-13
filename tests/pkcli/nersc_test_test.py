"""Test pkcli.nersc_test

:copyright: Copyright (c) 2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
import pytest


def test_conformance():
    _do(
        "nersc_test.sequential PASS",
        lambda s: s.strip(),
        [],
    )


def test_deviance():
    from pykern import pkunit

    _do(
        "nersc_test sequential fail: error=unexpected result state=error",
        lambda s: s.split("\n")[0],
        [f"--pkunit-deviance={pkunit.data_dir().join('failure_in.json.jinja')}"],
    )


def _do(expect, out_fn, cmd_arg):
    import subprocess
    from pykern import pkunit

    with pkunit.save_chdir_work():
        p = subprocess.run(
            ["sirepo", "nersc_test", "sequential"] + cmd_arg,
            capture_output=True,
            text=True,
        )
        pkunit.pkeq(
            expect,
            out_fn(p.stdout),
            "returncode={}\nstdout={}\nstderr={}",
            p.returncode,
            p.stdout,
            p.stderr,
        )
