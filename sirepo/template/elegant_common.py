# -*- coding: utf-8 -*-
u"""Common values for elegant

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdc, pkdlog
from sirepo.template import template_common
import os

SIM_TYPE = 'elegant'

#: Where to get files
RESOURCE_DIR = template_common.resource_dir(SIM_TYPE)


def sort_elements_and_beamlines(data):
    m = data['models']
    m.elements = sorted(m.elements, key=lambda e: (e.type, e.name.lower()))
    m.beamlines = sorted(m.beamlines, key=lambda e: e.name.lower())


def subprocess_env():
    """Adds RPN_DEFNS to os.environ

    Returns:
        dict: copy of env
    """
    return PKDict(os.environ).update(RPN_DEFNS=str(RESOURCE_DIR.join('defns.rpn')))


def subprocess_output(cmd):
    """Run cmd and return output or None, logging errors.

    Args:
        cmd (list): what to run
    Returns:
        str: output is None on error else a stripped string
    """
    return template_common.subprocess_output(cmd, subprocess_env())
