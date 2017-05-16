# -*- coding: utf-8 -*-
u"""Common values for elegant

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkdebug import pkdp, pkdc, pkdlog
from sirepo.template import template_common
import os
import subprocess


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


def subprocess_output(cmd):
    """Run cmd and return output or None, logging errors.

    Args:
        cmd (list): what to run
    Returns:
        str: output is None on error else a stripped string
    """
    err = None
    out = None
    try:

        p = subprocess.Popen(
            cmd,
            env=subprocess_env(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        out, err = p.communicate()
        if p.wait() != 0:
            raise subprocess.CalledProcessError(returncode=p.returncode, cmd=cmd)
    except subprocess.CalledProcessError as e:
        pkdlog('{}: exit={} err={}', cmd, e.returncode, err)
        return None
    if out != None and len(out):
        return out.strip()
    return ''
