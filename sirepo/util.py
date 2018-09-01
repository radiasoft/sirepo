# -*- coding: utf-8 -*-
u"""Utilities for requests

:copyright: Copyright (c) 2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkdebug import pkdlog
import werkzeug.exceptions


def raise_bad_request(*args, **kwargs):
    _raise('BadRequest', *args, **kwargs)


def raise_forbidden(*args, **kwargs):
    _raise('Forbidden', *args, **kwargs)


def raise_not_found(*args, **kwargs):
    _raise('NotFound', *args, **kwargs)


def merge_dicts(base, derived, depth = 1):
    if depth <= 0:
        return
    for key in base:
        if key not in derived:
            derived[key] = base[key]
        merge_dicts(base[key], derived[key], depth-1)

def merge_lists(base, derived):
    for item in base:
        derived.append(item)

def err(obj, format='', *args, **kwargs):
    return '{}: '.format(obj) + format.format(*args, **kwargs)


def _raise(exc, fmt, *args, **kwargs):
    pkdlog(fmt, *args, **kwargs)
    raise getattr(werkzeug.exceptions, exc)()
