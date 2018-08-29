# -*- coding: utf-8 -*-
u"""Utilities for requests

:copyright: Copyright (c) 2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkdebug import pkdlog
import werkzeug.exceptions


def raise_forbidden(fmt, *args, **kwargs):
    pkdlog(fmt, *args, **kwargs)
    raise werkzeug.exceptions.Forbidden()


def raise_not_found(fmt, *args, **kwargs):
    pkdlog(fmt, *args, **kwargs)
    raise werkzeug.exceptions.NotFound()

def merge_dicts(base, derived, depth = 1):
    if depth <= 0:
        return
    for key in base:
        if key not in derived:
            derived[key] = base[key]
        merge_dicts(base[key], derived[key], depth-1)

def err(obj, format='', *args, **kwargs):
    return '{}: '.format(obj) + format.format(*args, **kwargs)
