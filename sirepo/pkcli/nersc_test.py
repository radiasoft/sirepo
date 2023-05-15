# -*- coding: utf-8 -*-
"""Nerc test suite

:copyright: Copyright (c) 2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdexc, pkdp, pkdlog
from pykern import pkio
from pykern import pksubprocess
import sirepo.sim_data

_SEQUENTIAL_TEST_BASH_FILE = "sequential_test.sh"
_SEQUENTIAL_TEST_JSON = "nersc_sequential.json"
_SIREPO_RUN_DIR = "sirepo_run_dir"

def sequential():

    s = pkio.py_path(_SIREPO_RUN_DIR)
    pkio.unchecked_remove(s)
    s.ensure(dir=True)
    b = f"""
#!/bin/bash
set -e
#rm -rf 'sirepo_run_dir'
#mkdir 'sirepo_run_dir'
cd 'sirepo_run_dir'
export SIREPO_MPI_CORES='1'
export PYKERN_PKCONFIG_CHANNEL='dev'
export PYKERN_PKDEBUG_WANT_PID_TIME='1'
export PYTHONUNBUFFERED='1'
export SIREPO_AUTH_LOGGED_IN_USER='someuser'
export SIREPO_JOB_MAX_MESSAGE_BYTES='200000000'
export SIREPO_SIMULATION_DB_LOGGED_IN_USER='someuser'
export SIREPO_SRDB_ROOT=$PWD
export PYTHONPATH=''
export PYTHONSTARTUP=''
perl -p -e "s<{s.basename}><$PWD>" '{sirepo.sim_data.get_class("srw").resource_path(_SEQUENTIAL_TEST_JSON)}' > 'jobCmdIn.json'
exec 'sirepo' 'job_cmd' 'jobCmdIn.json'
    """
    pkio.write_text(_SEQUENTIAL_TEST_BASH_FILE, b)
    pksubprocess.check_call_with_signals(
        ["bash", _SEQUENTIAL_TEST_BASH_FILE]
    )
    pkio.unchecked_remove(_SEQUENTIAL_TEST_BASH_FILE)

    # TODO (gurhar1133): make sure "state":"completed"