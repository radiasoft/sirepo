# -*- coding: utf-8 -*-
u"""uri formatting

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pykern.pkinspect
import re

try:
    # py3
    from urllib.parse import urlencode, quote
except ImportError:
    # py2
    from urllib import urlencode, quote


def api(*args, **kwargs):
    """Alias for `uri_router.uri_for_api`"""
    return uri_router.uri_for_api(*args, **kwargs)


def app_root(sim_type):
    """Generate uri for application root

    Args:
        sim_type (str): application name [flask.g.sirepo_sim_type]

    Returns:
        str: formatted URI
    """
    t = http_request.sim_type(sim_type)
    return '/' if t is None else '/' + t


def default_local_route_name(schema):
    for k, v in schema.localRoutes.items():
        if v.get('isDefault'):
            return k
    else:
        raise AssertionError(
            'no isDefault in localRoutes for {}'.format(schema.simulationType),
        )


def init(**imports):
    import sirepo.util

    sirepo.util.setattr_imports(imports)


def local_route(sim_type, route_name=None, params=None, query=None):
    """Generate uri for local route with params

    Args:
        sim_type (str): application name
        route_name (str): a local route [defaults to local default]
        params (dict): paramters to pass to route
        query (dict): query values (joined and escaped)
    Returns:
        str: formatted URI
    """
    t = http_request.sim_type(sim_type)
    s = simulation_db.get_schema(t)
    if not route_name:
        route_name = default_local_route_name(s)
    parts = s.localRoutes[route_name].route.split('/:')
    u = parts.pop(0)
    for p in parts:
        if p.endswith('?'):
            p = p[:-1]
            if not params or p not in params:
                continue
        u += '/' + _to_uri(params[p])
    return app_root(t) + '#' + u + _query(query)


def server_route(route_or_uri, params, query):
    """Convert name to uri found in SCHEMA_COMMON

    Args:
        route_or_uri (str): route or uri
        params (dict): parameters to apply to route
        query (dict): query string values

    Returns:
        str: URI
    """
    if '/' in route_or_uri:
        assert not params and not query, \
            'when uri={} must not have params={} or query={}'.format(
                route_or_uri,
                params,
                query,
            )
        return route_or_uri
    route = simulation_db.SCHEMA_COMMON['route'][route_or_uri]
    if params:
        for k, v in params.items():
            k2 = r'\??<' + k + '>'
            n = re.sub(k2, _to_uri(str(v)), route)
            assert n != route, \
                '{}: not found in "{}"'.format(k2, route)
            route = n
    route = re.sub(r'\??<[^>]+>', '', route)
    assert not '<' in route, \
        '{}: missing params'.format(route)
    route += _query(query)
    return route


def _query(query):
    if not query:
        return ''
    return '?' + urlencode(query)


def _to_uri(element):
    if isinstance(element, bool):
        return str(int(element))
    return quote(element, safe="()-_.!~*'")
