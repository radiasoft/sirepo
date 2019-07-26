# -*- coding: utf-8 -*-
u"""Common values for elegant

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkdebug import pkdp, pkdc, pkdlog
from sirepo.template import template_common
import os


#: Application name
SIM_TYPE = 'elegant'

#: Where to get files
RESOURCE_DIR = template_common.resource_dir(SIM_TYPE)


def sort_elements_and_beamlines(data):
    models = data['models']
    data['models']['elements'] = sorted(models['elements'], key=lambda el: el['type'])
    data['models']['elements'] = sorted(models['elements'], key=lambda el: (el['type'], el['name'].lower()))
    data['models']['beamlines'] = sorted(models['beamlines'], key=lambda b: b['name'].lower())


def subprocess_env():
    """Adds RPN_DEFNS to os.environ

    Returns:
        dict: copy of env
    """
    res = os.environ.copy()
    res['RPN_DEFNS'] = str(RESOURCE_DIR.join('defns.rpn'))
    return res


def subprocess_output(cmd):
    """Run cmd and return output or None, logging errors.

    Args:
        cmd (list): what to run
    Returns:
        str: output is None on error else a stripped string
    """
    return template_common.subprocess_output(cmd, subprocess_env())
