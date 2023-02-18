# -*- coding: utf-8 -*-
"""Run Python processes in background

:copyright: Copyright (c) 2016 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern import pkconfig
from pykern.pkcollections import json_load_any, PKDict


def assert_project(project, quota):
    if not project:
        return ""
    assert any([project in o.fs for o in quota]), invalid_project_msg(project)
    return sbatch_account(project)


def sbatch_account(project):
    return f"#SBATCH --account={project}"


def invalid_project_msg(project):
    return f"sbatchProject={project} is invalid"