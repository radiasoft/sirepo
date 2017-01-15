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

#: Where to route when no routes match (root)
_default_route = None

#: When there is no uri (homePage)
_empty_route = None

#: dict of base_uri to route (base_uri, func, name, decl_uri, params)
_map = None

def init(app, api_module, simulation_db):
    """Convert route map to dispatchable callables

    Initializes `_map` and adds a single flask route (`_dispatch`) to
    dispatch based on the map.

    Args:
        app (Flask): flask app
        api_module (module): where to get callables
    """
    global _map
    if _map:
        # Already initialized
        return
    global _default_route, _empty_route, sr_unit_uri
    _map = pkcollections.Dict()
    for k, v in simulation_db.SCHEMA_COMMON.route.items():
        r = _split_uri(v)
        r.decl_uri = v
        r.func = api_module['api_' + k]
        r.name = k
        assert not r.base_uri in _map, \
            '{}: duplicate end point; other={}'.format(v, routes[r.base_uri])
        _map[r.base_uri] = r
        if r.base_uri == '':
            _default_route = r
        if 'sr_unit' in v:
            sr_unit_uri = v
    assert _default_route, \
        'missing default route'
    # 'light' is the homePage, not 'root'
    _empty_route = _map.light
    app.add_url_rule('/<path:path>', '_dispatch', _dispatch, methods=('GET', 'POST'))
    app.add_url_rule('/', '_dispatch_empty', _dispatch_empty, methods=('GET', 'POST'))


def _dispatch(path):
    """Called by Flask and routes the base_uri with parameters

    Args:
        path (str): what to route

    Returns:
        Flask.response
    """
    try:
        if path is None:
            return _empty_route.func()
        parts = path.split('/')
        try:
            route = _map[parts[0]]
            parts.pop(0)
        except KeyError:
            route = _default_route
        kwargs = pkcollections.Dict()
        for p in route.params:
            if not parts:
                if not p.optional:
                    werkzeug.exceptions.abort(404)
                    pkdlog('{}: uri missing parameter ({})', path, p.name)
                break
            kwargs[p.name] = parts.pop(0)
        if parts:
            pkdlog('{}: unknown parameters in uri ({})', parts, path)
            werkzeug.exceptions.abort(404)
        return route.func(**kwargs)
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
