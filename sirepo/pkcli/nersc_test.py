# -*- coding: utf-8 -*-
"""allow NERSC to run tests of Sirepo images in their infrastructure

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
import shutil


_SEQUENTIAL_BASH_FILE = "sequential_test.sh"
_RESOURCE_DIR = "nersc_test/"
_RUN_DIR = "sirepo_run_dir"
_SEQUENTIAL_JOB_CMD_INPUT = "nersc_sequential.json"
_SEQUENTIAL_RESULT_FILE = "nersc_sequential.log"


def sequential():
    """Sequential testing of job_cmd for nersc. Generates bash script
    that invokes job_cmd on a srw in.json with one MPI core.
    """
    try:
        s = pykern.pkio.py_path(_RUN_DIR)
        pykern.pkio.unchecked_remove(s)
        s.ensure(dir=True)
        o = s.join(_SEQUENTIAL_RESULT_FILE)
        for f in (_SEQUENTIAL_JOB_CMD_INPUT, _SEQUENTIAL_BASH_FILE):
            _render(f, s)
        pykern.pksubprocess.check_call_with_signals(
            ["bash", s.join(_SEQUENTIAL_BASH_FILE)],
            output=str(o),
        )
        r = pykern.pkjson.load_any(o)
        if r.state != "completed":
            raise RuntimeError(f"incomplete result {r.state}")
        return "nersc_test.sequential PASS"
    except Exception as e:
        return f"nersc_test sequential fail: error={e}\n{pkdexc()}\nunix_uid={os.geteuid()}"


def _file_path(filename):
    return sirepo.resource.file_path(
        _RESOURCE_DIR + filename + pykern.pkjinja.RESOURCE_SUFFIX
    )


def _render(filename, run_dir):
    pykern.pkjinja.render_file(
        _file_path(filename),
        PKDict(
            user=sirepo.const.MOCK_UID,
            sirepo_run_dir=run_dir,
            jobCmdIn=run_dir.join(_SEQUENTIAL_JOB_CMD_INPUT),
        ),
        output=run_dir.join(filename),
    )
