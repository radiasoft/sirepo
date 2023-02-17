# -*- coding: utf-8 -*-
"""Run Python processes in background

:copyright: Copyright (c) 2016 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern import pkconfig
from pykern.pkcollections import json_load_any, PKDict

VALID_PROJECT = "VALID_PROJECT"

_NERSC_HPSS_QUOTA = [
    PKDict(
        fs=f"{VALID_PROJECT}",
        inode_perc="0.0%",
        space_perc="0.0%",
    ),
]


def assert_project(project):
    if not project:
        return ""
    assert any([project in o.fs for o in get_quota()]), f"sbatchProject={project} is invalid"
    return f"#SBATCH --account={project}"


def get_quota():
    import subprocess
    if pkconfig.channel_in("dev"):
        return _NERSC_HPSS_QUOTA
    return json_load_any(subprocess.check_output(["hpssquota", "-J"], text=True))

