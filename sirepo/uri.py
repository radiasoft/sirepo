# -*- coding: utf-8 -*-
"""uri formatting

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp
import pykern.pkcompat
import pykern.pkinspect
import re
import sirepo.feature_config
import urllib.parse

#: route parsing
PARAM_RE = r"([\?\*]?)<{}>"

#: optional parameter that consumes rest of parameters
PATH_INFO_CHAR = "*"

# TODO(robnagler): make class that gets returned


def app_root(sim_type=None):
    """Generate uri for application root

    Args:
        sim_type (str): application name [None]
    Returns:
        str: formatted URI
    """
    return uri_router.uri_for_api(
        "root",
        params=PKDict(path_info=sim_type) if sim_type else None,
    )


def decode_to_str(encoded):
    return pykern.pkcompat.from_bytes(urllib.parse.unquote_to_bytes(encoded))


def default_local_route_name(schema):
    return schema.appDefaults.route


def init_module(**imports):
    import sirepo.util

    # import simulation_db, uri_router
    sirepo.util.setattr_imports(imports)


def local_route(sim_type, route_name=None, params=None, query=None):
    """Generate uri for local route with params

    Args:
        sim_type (str): simulation type (must be valid)
        route_name (str): a local route [defaults to local default]
        params (dict): paramters to pass to route
        query (dict): query values (joined and escaped)
    Returns:
        str: formatted URI
    """
    s = simulation_db.get_schema(sim_type)
    if not route_name:
        route_name = default_local_route_name(s)
    parts = s.localRoutes[route_name].route.split("/:")
    u = parts.pop(0)
    for p in parts:
        if p.endswith("?"):
            p = p[:-1]
            if not params or p not in params:
                continue
        u += "/" + _to_uri(params[p])
    return app_root(sim_type) + "#" + u + _query(query)


def is_sr_exception_only(sim_type, route_name):
    """local route has srExceptionOnly param

    Args:
        sim_type (str): simulation type (must be valid)
        route_name (str): a local route
    Returns:
        object: True if srExceptionOnly, else False; None if route not found
    """
    rv = simulation_db.get_schema(sim_type).localRoutes.get(route_name).route
    return rv and "srExceptionOnly" in rv


def server_route(route_or_uri, params, query):
    """Convert name to uri found in SCHEMA_COMMON

    Args:
        route_or_uri (str): route or uri
        params (dict): parameters to apply to route
        query (dict): query string values
    Returns:
        str: URI
    """
    if "/" in route_or_uri:
        assert (
            not params and not query
        ), "when uri={} must not have params={} or query={}".format(
            route_or_uri,
            params,
            query,
        )
        return route_or_uri
    route = simulation_db.SCHEMA_COMMON["route"][route_or_uri]
    if params:
        for k, v in params.items():
            k2 = PARAM_RE.format(k)
            n = re.sub(k2, _to_uri(str(v)), route)
            assert n != route, '{}: not found in "{}"'.format(k2, route)
            route = n
    route = re.sub(r"\??<[^>]+>", "", route)
    assert not "<" in route, "{}: missing params".format(route)
    route += _query(query)
    return route


def unchecked_root_redirect(path):
    return simulation_db.SCHEMA_COMMON.rootRedirectUri.get(path)


def _query(query):
    if not query:
        return ""
    return "?" + urllib.parse.urlencode(query)


def _to_uri(element):
    if isinstance(element, bool):
        return str(int(element))
    return urllib.parse.quote(element, safe="()-_.!~*'")
