# -*- coding: utf-8 -*-
"""Methods related to running on NERSC

:copyright: Copyright (c) 2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
import re
import subprocess
import sirepo.util
from pykern import pkconfig
from pykern.pkcollections import PKDict


_ACCOUNT_NOT_FOUND = "no such fileset"

VALID_TEST_ACCOUNT = "VALID_TEST_ACCOUNT"


def sbatch_project_option(project):
    if not project:
        return ""
    res = (
        _test_res(project)
        if pkconfig.channel_in_internal_test()
        else subprocess.run(
            ("hpssquota", project),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
    )
    assert not re.search(_ACCOUNT_NOT_FOUND, res.stdout), invalid_project_msg(project)
    return sbatch_account(project)


def sbatch_account(project):
    return f"#SBATCH --account={project}"


def invalid_project_msg(project):
    return f"sbatchProject={project} is invalid"


def _test_res(project):
    return PKDict(stdout="" if project == VALID_TEST_ACCOUNT else _ACCOUNT_NOT_FOUND)
