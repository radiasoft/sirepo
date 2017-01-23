# -*- coding: utf-8 -*-
u"""Handles dispatching of uris to server.api_* functions

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkcollections
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp
import re

#: route for sirepo.sr_unit
sr_unit_uri = None

#: route parsing
_PARAM_RE = re.compile(r'^(\??)<(.+?)>$')

#: prefix for api functions
_FUNC_PREFIX = 'api_'

#: Where to route when no routes match (root)
_default_route = None

#: When there is no uri (homePage)
_empty_route = None

#: dict of base_uri to route (base_uri, func, name, decl_uri, params)
_uri_to_route = None

#: dict of base_uri to route (base_uri, func, name, decl_uri, params)
_api_to_route = None


class NotFound(Exception):
    """Raised to indicate page not found exception (404)"""
    def __init__(self, log_fmt, *args, **kwargs):
        super(NotFound, self).__init__()
        self.log_fmt = log_fmt
        self.args = args
        self.kwargs = kwargs


def api_for_func(func):
    """Returns api name for given function

    Args:
        func (code): for __name__

    Returns:
        str: name of api
    """
    n = func.__name__
    assert n.startswith(_FUNC_PREFIX), \
        '{}: not an api function'.format(n)
    return n[len(_FUNC_PREFIX):]


def func_for_api(api_name, api_module):
    """Returns func for given api name and module

    Args:
        api_name (str): camelCase
        api_module (module): where from

    Returns:
        code: what to call
    """
    import types

    res = getattr(api_module, _FUNC_PREFIX + api_name, None)
    # Be very restrictive for this since we are calling arbitrary code
    assert res and isinstance(res, types.FunctionType), \
        '{}: unknown api in {}'.format(api_name, api_module.__name__)
    return res


def init(app, api_module, simulation_db):
    """Convert route map to dispatchable callables

    Initializes `_uri_to_route` and adds a single flask route (`_dispatch`) to
    dispatch based on the map.

    Args:
        app (Flask): flask app
        api_module (module): where to get callables
    """
    global _uri_to_route
    if _uri_to_route:
        # Already initialized
        return
    global _default_route, _empty_route, sr_unit_uri, _api_to_route
    _uri_to_route = pkcollections.Dict()
    _api_to_route = pkcollections.Dict()
    for k, v in simulation_db.SCHEMA_COMMON.route.items():
        r = _split_uri(v)
        r.decl_uri = v
        r.func = func_for_api(k, api_module)
        r.name = k
        assert not r.base_uri in _uri_to_route, \
            '{}: duplicate end point; other={}'.format(v, routes[r.base_uri])
        _uri_to_route[r.base_uri] = r
        _api_to_route[k] = r
        if r.base_uri == '':
            _default_route = r
        if 'sr_unit' in v:
            sr_unit_uri = v
    assert _default_route, \
        'missing default route'
    # 'light' is the homePage, not 'root'
    _empty_route = _uri_to_route.light
    app.add_url_rule('/<path:path>', '_dispatch', _dispatch, methods=('GET', 'POST'))
    app.add_url_rule('/', '_dispatch_empty', _dispatch_empty, methods=('GET', 'POST'))


def uri_for_api(api_name, params=None):
    """Generate uri for api method

    Args:
        api_name (str): full name of api
        params (str): paramters to pass to uri

    Returns:
g        str: formmatted external URI
    """
    import flask
    import urllib

    r = _api_to_route[api_name]
    http = (flask.url_for('_dispatch_empty', _external=True) + r.base_uri).rstrip('/')
    for p in r.params:
        if p.name in params:
            http += '/' + params[p.name]
            continue
        assert p.optional, \
            '{}: missing parameter for api ({})'.format(p.name, api_name)
    return http


def _dispatch(path):
    """Called by Flask and routes the base_uri with parameters

    Args:
        path (str): what to route

    Returns:
        Flask.response
    """
    import werkzeug.exceptions
    try:
        if path is None:
            return _empty_route.func()
        parts = path.split('/')
        try:
            route = _uri_to_route[parts[0]]
            parts.pop(0)
        except KeyError:
            route = _default_route
        kwargs = pkcollections.Dict()
        for p in route.params:
            if not parts:
                if not p.optional:
                    raise NotFound('{}: uri missing parameter ({})', path, p.name)
                break
            kwargs[p.name] = parts.pop(0)
        if parts:
            raise NotFound('{}: unknown parameters in uri ({})', parts, path)
        return route.func(**kwargs)
    except NotFound as e:
        #TODO(robnagler) cascade calling context
        pkdlog(e.log_fmt, *e.args, **e.kwargs)
        raise werkzeug.exceptions.NotFound()
    except Exception as e:
        pkdlog('{}: error: {}', path, pkdexc())
        raise


def _dispatch_empty():
    """Hook for '/' route"""
    return _dispatch(None)


def _split_uri(uri):
    """Parse the URL for parameters

    Args:
        uri (str): full path with parameter args in flask format

    Returns:
        Dict: with base_uri, func, params, etc.
    """
    parts = uri.split('/')
    assert '' == parts.pop(0)
    params = []
    res = pkcollections.Dict(params=params)
    in_optional = False
    first = None
    for p in parts:
        m = _PARAM_RE.search(p)
        if not m:
            assert first is None, \
                '{}: too many non-paramter components of uri'.format(uri)
            first = p
            continue
        rp = pkcollections.Dict()
        params.append(rp)
        rp.optional = bool(m.group(1))
        rp.name = m.group(2)
        if rp.optional:
            in_optional = True
        else:
            assert not in_optional, \
                '{}: optional parameter ({}) followed by non-optional'.format(
                    uri,
                    rp.name,
                )
    res.base_uri = first or ''
    return res
