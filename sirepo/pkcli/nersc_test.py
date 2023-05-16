# -*- coding: utf-8 -*-
"""NERSC test suite

:copyright: Copyright (c) 2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdexc, pkdp, pkdlog
import pykern.pkio
import pykern.pkjson
import pykern.pksubprocess
import pykern.pkjinja
import sirepo.sim_data
import sirepo.const
import sirepo.resource
import shutil


_SEQUENTIAL_TEST_BASH_FILE = "sequential_test.sh"
_SEQUENTIAL_TEST_BASH_TEMPLATE = _SEQUENTIAL_TEST_BASH_FILE + ".jinja"
_NERSC_TEST_DIR = "nersc_test/"
_SEQUENTIAL_TEST_JSON = "nersc_sequential.json"
_RUN_DIR = "sirepo_run_dir"
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
        shutil.copyfile(
            _file(_SEQUENTIAL_TEST_BASH_TEMPLATE),
            s.join(_SEQUENTIAL_TEST_BASH_TEMPLATE),
        )
        pykern.pkjinja.render_file(
            s.join(_SEQUENTIAL_TEST_BASH_TEMPLATE),
            PKDict(
                user=sirepo.const.MOCK_UID,
                sirepo_run_dir=s.basename,
                json_in_path=_file(_SEQUENTIAL_TEST_JSON),
            ),
            output=s.join(_SEQUENTIAL_TEST_BASH_FILE),
        )
        pykern.pksubprocess.check_call_with_signals(
            ["bash", s.join(_SEQUENTIAL_TEST_BASH_FILE)],
            output=str(o),
        )
        r = pykern.pkjson.load_any(o)
        if r.state != "completed":
            raise RuntimeError(f"incomplete result {r.state}")
        return "nersc_test.sequential PASS"
    except Exception as e:
        return e


def _file(filename):
    return sirepo.resource.file_path(_NERSC_TEST_DIR + filename)
