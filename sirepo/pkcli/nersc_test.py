# -*- coding: utf-8 -*-
"""Allow NERSC to run tests of Sirepo images in their infrastructure

:copyright: Copyright (c) 2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdexc, pkdp, pkdlog
import os
import pykern.pkio
import pykern.pkjson
import pykern.pksubprocess
import pykern.pkjinja
import sirepo.sim_data
import sirepo.const
import sirepo.resource


def sequential(*args):
    """Test sequential process for use by NERSC inside SHIFTER

    Simulates the operation that Sirepo does when it executes a
    sequential process on a login node in SHIFTER.

    On success, will return (output) ``nersc_test.sequential PASS``

    Returns:
        str: PASS or fail with diagnostic information
    """
    s = _Sequential()
    try:
        s.prepare(args)
        s.execute()
        return "nersc_test.sequential PASS"
    except Exception as e:
        return f"nersc_test sequential fail: error={e}\nunix_uid={os.geteuid()}\n{s}{pkdexc()}"


class _Sequential(PKDict):
    """Run a sequential job by mocking the input to job_cmd"""

    JOB_CMD_FILE = "sequential_job_cmd.json"
    RESOURCE_DIR = "nersc_test/"
    RESULT_FILE = "sequential_result.json"
    RUN_DIR = "sirepo_run_dir"
    RUN_FILE = "sequential_run.sh"

    def prepare(self, args=None):
        self.run_dir = pykern.pkio.py_path(self.RUN_DIR)
        pykern.pkio.unchecked_remove(self.run_dir)
        self.run_dir.ensure(dir=True)
        self.result_file = self.run_dir.join(self.RESULT_FILE)
        self.user = sirepo.const.MOCK_UID
        self.job_cmd_file = self._render_resource(self.JOB_CMD_FILE, args=args)
        self.run_file = self._render_resource(self.RUN_FILE)

    def execute(self):
        pykern.pksubprocess.check_call_with_signals(
            ["bash", self.run_file],
            output=str(self.result_file),
        )
        self.result_text = pykern.pkio.read_text(self.result_file)
        self.result_parsed = pykern.pkjson.load_any(self.result_text)
        if self.result_parsed.state != "completed":
            raise RuntimeError(f"unexpected result state={self.result_parsed.state}")

    def _file_path(self, filename):
        return sirepo.resource.file_path(
            self.RESOURCE_DIR + filename + pykern.pkjinja.RESOURCE_SUFFIX
        )

    def __str__(self):
        res = "Internal state:\n"
        for k in ("run_dir", "run_file", "result_file"):
            res += f"{k}={self.get(k)}\n"
        if "result_text" in self:
            if "result_parsed" in self:
                res += "result_parsed=" + pykern.pkjson.dump_pretty(self.result_parsed)
            else:
                res += "result_text=" + self.result_text
        return res

    def _render_resource(self, filename, args=None):
        res = self.run_dir.join(filename)
        p = self._valid_args(args)
        pykern.pkjinja.render_file(
            p if p else self._file_path(filename),
            PKDict(
                job_cmd_file=self.get("job_cmd_file"),
                run_dir=self.run_dir,
                user=self.user,
            ),
            output=res,
        )
        return res

    def _valid_args(self, args):
        if not args:
            return None
        a = args[0].split("=")
        if a[0] == "job_cmd_in_path":
            return a[1]
        raise RuntimeError(f"Invalid argument {a[0]} passed to sequential")
