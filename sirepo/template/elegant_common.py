# -*- coding: utf-8 -*-
"""Common values for elegant

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdc, pkdlog
from sirepo.template import template_common
import sirepo.sim_data
import os

_SIM_DATA, SIM_TYPE, SCHEMA = sirepo.sim_data.template_globals("elegant")


def subprocess_env():
    """Adds RPN_DEFNS to os.environ

    Returns:
        dict: copy of env
    """
    return PKDict(os.environ).pkupdate(
        RPN_DEFNS=str(_SIM_DATA.resource_path("defns.rpn")),
    )


def subprocess_output(cmd):
    """Run cmd and return output or None, logging errors.

    Args:
        cmd (list): what to run
    Returns:
        str: output is None on error else a stripped string
    """
    return template_common.subprocess_output(cmd, subprocess_env())
