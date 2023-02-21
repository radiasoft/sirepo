# -*- coding: utf-8 -*-
"""Methods related to running on NERSC

:copyright: Copyright (c) 2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
import re
import subprocess
import sirepo.util

ACCOUNT_NOT_FOUND = "no such fileset"


def sbatch_project_option(project):
    if not project:
        return ""
    res = _hpssquota(project)
    if re.search(ACCOUNT_NOT_FOUND, res.stdout):
        raise sirepo.util.UserAlert(f"Account {project} not found on NERSC")
    return sbatch_account(project)


def sbatch_account(project):
    return f"#SBATCH --account={project}"


def invalid_project_msg(project):
    return f"sbatchProject={project} is invalid"


def _hpssquota(project):
    return subprocess.run(
        ("hpssquota", project),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

