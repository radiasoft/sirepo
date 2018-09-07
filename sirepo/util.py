# -*- coding: utf-8 -*-
u"""Utilities for requests

:copyright: Copyright (c) 2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkdebug import pkdlog
import numconv
import random
import werkzeug.exceptions


def err(obj, format='', *args, **kwargs):
    return '{}: '.format(obj) + format.format(*args, **kwargs)


def raise_bad_request(*args, **kwargs):
    _raise('BadRequest', *args, **kwargs)

def raise_forbidden(*args, **kwargs):
    _raise('Forbidden', *args, **kwargs)

def raise_not_found(*args, **kwargs):
    _raise('NotFound', *args, **kwargs)


def raise_unauthorized(*args, **kwargs):
    _raise('Unauthorized', *args, **kwargs)


def random_base62(length=32):
    """Returns a safe string of sufficient length to be a nonce

    Args:
        length (int): how long to make the base62 string [32]
    Returns:
        str: random base62 characters
    """
    r = random.SystemRandom()
    return ''.join(r.choice(numconv.BASE62) for x in range(length))


def _raise(exc, fmt, *args, **kwargs):
    pkdlog(fmt, *args, **kwargs)
    raise getattr(werkzeug.exceptions, exc)()
