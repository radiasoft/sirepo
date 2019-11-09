# -*- coding: utf-8 -*-
u"""Support routines and classes, mostly around errors.

:copyright: Copyright (c) 2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdlog, pkdp
import inspect
import numconv
import random
import werkzeug.exceptions


class Reply(Exception):
    """Raised to end the request.

    Args:
        sr_args (dict): exception args that Sirepo specific
        log_fmt (str): server side log data
    """
    def __init__(self, sr_args, *args, **kwargs):
        super(Reply, self).__init__()
        if args or kwargs:
            kwargs['pkdebug_frame'] = inspect.currentframe().f_back.f_back
            pkdlog(*args, **kwargs)
        self.sr_args = sr_args

    def __repr__(self):
        a = self.sr_args
        return '{}({})'.format(
            self.__class__.__name__,
            ','.join(
                ('{}={}'.format(k, a[k]) for k in sorted(a.keys())),
            )
        )

    def __str__(self):
        return self.__repr__()


class Error(Reply):
    """Raised to send an error response

    Args:
        values (dict): values to put in the reply
    """
    def __init__(self, values, *args, **kwargs):
        assert values.get('error'), \
            'values={} must contain "error"'.format(values)
        super(Error, self).__init__(
            PKDict(values),
            *args,
            **kwargs
        )


class Redirect(Reply):
    """Raised to redirect

    Args:
        uri (str): where to redirect to
        log_fmt (str): server side log data
    """
    def __init__(self, uri, *args, **kwargs):
        super(Redirect, self).__init__(
            PKDict(uri=uri),
            *args,
            **kwargs
        )


class SRException(Reply):
    """Raised to communicate a local redirect and log info

    Args:
        route_name (str): a local route
        params (dict): parameters for route
        query (dict): extract arguments (e.g. reload_js)
        log_fmt (str): server side log data
    """
    def __init__(self, route_name, params, query, *args, **kwargs):
        super(SRException, self).__init__(
            PKDict(routeName=route_name, params=params, query=query),
            *args,
            **kwargs
        )


class UserAlert(Reply):
    """Raised to display a user error and log info

    Args:
        display_text (str): string that user will see
        log_fmt (str): server side log data
    """
    def __init__(self, display_text, *args, **kwargs):
        super(UserAlert, self).__init__(
            PKDict(error=display_text),
            *args,
            **kwargs
        )


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
    kwargs['pkdebug_frame'] = inspect.currentframe().f_back.f_back
    pkdlog(fmt, *args, **kwargs)
    raise getattr(werkzeug.exceptions, exc)()
