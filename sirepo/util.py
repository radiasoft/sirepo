# -*- coding: utf-8 -*-
u"""Support routines and classes, mostly around errors.

:copyright: Copyright (c) 2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkdebug import pkdlog
import numconv
import random
import werkzeug.exceptions


class UserAlert(Exception):
    """Raised to display a user error and log info

    Args:
        display_text (str): string that user will see
        log_fmt (str): server side log data
    """
    def __init__(self, display_text, log_fmt, *args, **kwargs):
        super(UserAlert, self).__init__()
        pkdlog(log_fmt, *args, **kwargs)
        self.display_text = display_text


def err(obj, fmt='', *args, **kwargs):
    return '{}: '.format(obj) + fmt.format(*args, **kwargs)


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
