# -*- coding: utf-8 -*-
u"""Support routines and classes, mostly around errors and I/O.

:copyright: Copyright (c) 2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkcompat
from pykern import pkconfig
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdlog, pkdp, pkdexc
import asyncio
import base64
import concurrent.futures
import contextlib
import hashlib
import inspect
import numconv
import pykern.pkinspect
import pykern.pkio
import pykern.pkjson
import random
import threading


cfg = None

#: All types of errors async code may throw when canceled
ASYNC_CANCELED_ERROR = (asyncio.CancelledError, concurrent.futures.CancelledError)

#: Http auth header name
AUTH_HEADER = 'Authorization'

#: http auth header scheme bearer
AUTH_HEADER_SCHEME_BEARER = 'Bearer'

#: Context where we can do sim_db_file operations (supervisor)
SIM_DB_FILE_LOCK = None

#: Locking for global simulation_db operations (server)
SIMULATION_DB_LOCK = None

#: length of string returned by create_token
TOKEN_SIZE = 16


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
        values (dict or str): values to put in the reply or just the error
    """
    def __init__(self, values, *args, **kwargs):
        if isinstance(values, pkconfig.STRING_TYPES):
            values = PKDict(error=values)
        else:
            assert values.get('error'), \
                'values={} must contain "error"'.format(values)
        super(Error, self).__init__(
            values,
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


class Response(Reply):
    """Raise with a Response object

    Args:
        response (str): what the reply should be
        log_fmt (str): server side log data
    """
    def __init__(self, response, *args, **kwargs):
        super(Response, self).__init__(
            PKDict(response=response),
            *args,
            **kwargs
        )


class SRException(Reply):
    """Raised to communicate a local redirect and log info

    `params` may have ``sim_type`` and ``reload_js``, which
    will be used to control execution and uri rendering.

    Args:
        route_name (str): a local route
        params (dict): parameters for route and redirect
        log_fmt (str): server side log data
    """
    def __init__(self, route_name, params, *args, **kwargs):
        super(SRException, self).__init__(
            PKDict(routeName=route_name, params=params),
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


def convert_exception(exception, display_text='unexpected error'):
    """Convert exception so can be raised

    Args:
        exception (Exception): Reply or other exception
        display_text (str): what to send back to the client
    Returns:
        Exception: to raise
    """
    if isinstance(exception, Reply):
        return exception
    return UserAlert(display_text, 'exception={} str={} stack={}', type(exception), exception, pkdexc())


def create_token(value):
    if pkconfig.channel_in_internal_test() and cfg.create_token_secret:
        v = base64.b32encode(
            hashlib.sha256(pkcompat.to_bytes(value + cfg.create_token_secret)).digest())
        return pkcompat.from_bytes(v[:TOKEN_SIZE])
    return random_base62(TOKEN_SIZE)



def err(obj, fmt='', *args, **kwargs):
    return '{}: '.format(obj) + fmt.format(*args, **kwargs)


def flask_app():
    import flask

    return flask.current_app or None


def init(server_context=False):
    global cfg, SIMULATION_DB_LOCK, SIM_DB_FILE_LOCK

    assert not cfg
    cfg = pkconfig.init(
        create_token_secret=('oh so secret!', str, 'used for internal test only'),
    )
    if server_context:
        SIMULATION_DB_LOCK = threading.RLock()
        return
    # Use nullcontext instead of an actual lock because supervisor is in tornado
    # which is single threaded
    SIM_DB_FILE_LOCK = contextlib.nullcontext()


def json_dump(obj, path=None, pretty=False, **kwargs):
    """Formats as json as string, and writing atomically to disk

    Args:
        obj (object): any Python object
        path (py.path): where to write (atomic) [None]
        pretty (bool): pretty print [False]
        kwargs (object): other arguments to `json.dumps`

    Returns:
        str: sorted and formatted JSON
    """
    res = pykern.pkjson.dump_pretty(obj, pretty=pretty, allow_nan=False, **kwargs)
    if path:
        pykern.pkio.atomic_write(path, res)
    return res


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


def secure_filename(path):
    import werkzeug.utils

    return werkzeug.utils.secure_filename(path)


def setattr_imports(imports):
    m = pykern.pkinspect.caller_module()
    for k, v in imports.items():
        setattr(m, k, v)


def split_comma_delimited_string(s, f_type):
    import re
    return [f_type(x) for x in re.split(r'\s*,\s*', s)]


def url_safe_hash(value):
    return hashlib.md5(pkcompat.to_bytes(value)).hexdigest()


def _raise(exc, fmt, *args, **kwargs):
    import werkzeug.exceptions

    kwargs['pkdebug_frame'] = inspect.currentframe().f_back.f_back
    pkdlog(fmt, *args, **kwargs)
    raise getattr(werkzeug.exceptions, exc)()
