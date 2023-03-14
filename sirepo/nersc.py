# -*- coding: utf-8 -*-
"""Methods related to running on NERSC

:copyright: Copyright (c) 2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
import re
import subprocess
import sirepo.util


def sbatch_project_option(project):
    from pykern.pkjson import load_any

    if not project:
        return ""
    try:
        if not list(filter(lambda x: project in x.fs, load_any(_hpssquota(project)))):
            raise sirepo.util.UserAlert(f"Project {project} not found on NERSC")
    except Exception as e:
        raise sirepo.util.UserAlert(f"Cannot determine quota for {project}; error={e}")
    return f"#SBATCH --account={project}"


# Note: project is only used for unit tests
def _hpssquota(project=None):
    # -N excludes home and scratch file systems; -J outputs json
    return subprocess.run(
        ("hpssquota", "-N", "-J"),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    ).stdout
