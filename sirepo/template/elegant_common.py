# -*- coding: utf-8 -*-
u"""Common values for elegant

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from sirepo.template import template_common
import os

#: Application name
SIM_TYPE = 'elegant'

#: Where to get files
RESOURCE_DIR = template_common.resource_dir(SIM_TYPE)


def subprocess_env():
    """Adds RPN_DEFNS to os.environ

    Returns:
        dict: copy of env
    """
    res = os.environ.copy()
    res['RPN_DEFNS'] = str(RESOURCE_DIR.join('defns.rpn'))
    return res
