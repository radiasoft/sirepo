# -*- coding: utf-8 -*-
u"""Handles dispatching of uris to server.api_* functions

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkcollections
from pykern import pkinspect
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp
import flask
import importlib
import inspect
import re
import sirepo.api_auth
import sirepo.auth
import sirepo.cookie
import sirepo.http_reply
import sirepo.http_request
import sirepo.uri
import sirepo.util
import werkzeug.exceptions


#: route for sirepo.srunit
srunit_uri = None

#: optional parameter that consumes rest of parameters
_PATH_INFO_CHAR = '*'

#: route parsing
_PARAM_RE = re.compile(r'^([\?\*]?)<(.+?)>$')

#: prefix for api functions
_FUNC_PREFIX = 'api_'

#: modules that must be initialized. server must be first
_REQUIRED_MODULES = ('server', 'auth', 'srtime')

#: Where to route when no routes match (root)
_default_route = None

#: When there is no uri (homePage)
_empty_route = None

#: dict of base_uri to route (base_uri, func, name, decl_uri, params)
_uri_to_route = None

#: dict of base_uri to route (base_uri, func, name, decl_uri, params)
_api_to_route = None

#: modules which support APIs
_api_modules = []

#: functions which implement APIs
_api_funcs = pkcollections.Dict()


def call_api(func_or_name, kwargs=None, data=None):
    """Call another API with permission checks.

    Note: also calls `save_to_cookie`.

    Args:
        func_or_name (object): api function or name (without `api_` prefix)
        kwargs (dict): to be passed to API [None]
        data (dict): will be returned `http_request.parse_json`
    Returns:
        flask.Response: result
    """
    p = None
    s = None
    try:
        # must be first so exceptions have access to sim_type
        if kwargs:
            # Any (GET) uri will have simulation_type in uri if it is application
            # specific.
            s = sirepo.http_request.set_sim_type(kwargs.get('simulation_type'))
        f = func_or_name if callable(func_or_name) \
            else _api_to_route[func_or_name].func
        sirepo.api_auth.check_api_call(f)
        try:
            if data:
                p = sirepo.http_request.set_post(data)
            r = flask.make_response(f(**kwargs) if kwargs else f())
        finally:
            if data:
                sirepo.http_request.set_post(p)
    except Exception as e:
        if isinstance(e, (sirepo.util.Reply, werkzeug.exceptions.HTTPException)):
            pkdc('api={} exception={} stack={}', func_or_name, e, pkdexc())
        else:
            pkdlog('api={} exception={} stack={}', func_or_name, e, pkdexc())
        r = sirepo.http_reply.gen_exception(e)
    finally:
        # http_request tries to keep a valid sim_type so
        # this is ok to call (even if s is None)
        sirepo.http_request.set_sim_type(s)
    sirepo.cookie.save_to_cookie(r)
    return r


def init(app, simulation_db):
    """Convert route map to dispatchable callables

    Initializes `_uri_to_route` and adds a single flask route (`_dispatch`) to
    dispatch based on the map.

    Args:
        app (Flask): flask app
    """
    if _uri_to_route:
        return

    from sirepo import feature_config

    for n in _REQUIRED_MODULES + tuple(sorted(feature_config.cfg().api_modules)):
        register_api_module(importlib.import_module('sirepo.' + n))
    _init_uris(app, simulation_db, feature_config.cfg().sim_types)

    sirepo.http_request.init(
        simulation_db=simulation_db,
    )
    sirepo.http_reply.init(
        simulation_db=simulation_db,
    )
    sirepo.uri.init(
        http_reply=sirepo.http_reply,
        http_request=sirepo.http_request,
        simulation_db=simulation_db,
        uri_router=pkinspect.this_module(),
    )


def register_api_module(module=None):
    """Add caller_module to the list of modules which implements apis.

    The module must have methods: api_XXX which do not collide with
    other apis. It must also have init_apis(), which will be called unless
    it is already registered.

    Args:
        module (module): defaults to caller module
    """
    assert not _default_route, \
        '_init_uris already called. All APIs must registered at init'
    m = module or pkinspect.caller_module()
    if m in _api_modules:
        return
    # prevent recursion
    _api_modules.append(m)
    m.init_apis()
    # It's ok if there are no APIs
    for n, o in inspect.getmembers(m):
        if n.startswith(_FUNC_PREFIX) and inspect.isfunction(o):
            assert not n in _api_funcs, \
                'function is duplicate: func={} module={}'.format(n, m.__name__)
            _api_funcs[n] = o


def uri_for_api(api_name, params=None, external=True):
    """Generate uri for api method

    Args:
        api_name (str): full name of api
        params (str): paramters to pass to uri
        external (bool): external uri? [True]

    Returns:
        str: formmatted external URI
    """
    r = _api_to_route[api_name]
    res = (flask.url_for('_dispatch_empty', _external=external) + r.base_uri).rstrip('/')
    for p in r.params:
        if p.name in params:
            v = params[p.name]
            if not v is None and len(v) > 0:
                if not (p.is_path_info and v.startswith('/')):
                    res += '/'
                res += v
                continue
        assert p.is_optional, \
            'missing parameter={} for api={}'.format(p.name, api_name)
    return res


def _dispatch(path):
    """Called by Flask and routes the base_uri with parameters

    Args:
        path (str): what to route

    Returns:
        Flask.response
    """
    sirepo.auth.process_request()
    try:
        if path is None:
            return call_api(_empty_route.func, {})
        # werkzeug doesn't convert '+' to ' '
        parts = re.sub(r'\+', ' ', path).split('/')
        try:
            route = _uri_to_route[parts[0]]
            parts.pop(0)
        except KeyError:
            # sim_types (applications)
            route = _default_route
        kwargs = pkcollections.Dict()
        for p in route.params:
            if not parts:
                if not p.is_optional:
                    raise sirepo.util.raise_not_found('{}: uri missing parameter ({})', path, p.name)
                break
            if p.is_path_info:
                kwargs[p.name] = '/'.join([x.lstrip(_PATH_INFO_CHAR) for x in parts])
                parts = None
                break
            kwargs[p.name] = parts.pop(0)
        if parts:
            raise sirepo.util.raise_not_found('{}: unknown parameters in uri ({})', parts, path)
        return call_api(route.func, kwargs)
    except Exception as e:
        pkdlog('exception={} path={} stack={}', e, path, pkdexc())
        raise


def _dispatch_empty():
    """Hook for '/' route"""
    return _dispatch(None)


def _init_uris(app, simulation_db, sim_types):
    global _default_route, _empty_route, srunit_uri, _api_to_route, _uri_to_route

    assert not _default_route, \
        '_init_uris called twice'
    _uri_to_route = pkcollections.Dict()
    _api_to_route = pkcollections.Dict()
    for k, v in simulation_db.SCHEMA_COMMON.route.items():
        r = _split_uri(v)
        try:
            r.func = _api_funcs[_FUNC_PREFIX + k]
        except KeyError:
            pkdc('not adding api, because module not registered: uri={}', v)
            continue
        sirepo.api_auth.assert_api_def(r.func)
        r.decl_uri = v
        r.name = k
        assert not r.base_uri in _uri_to_route, \
            '{}: duplicate end point; other={}'.format(v, _uri_to_route[r.base_uri])
        _uri_to_route[r.base_uri] = r
        _api_to_route[k] = r
        if r.base_uri == '':
            _default_route = r
        if 'srunit' in v:
            srunit_uri = v
    assert _default_route, \
        'missing default route'
    _empty_route = _uri_to_route.en
    _validate_root_redirect_uris(_uri_to_route, simulation_db)
    app.add_url_rule('/<path:path>', '_dispatch', _dispatch, methods=('GET', 'POST'))
    app.add_url_rule('/', '_dispatch_empty', _dispatch_empty, methods=('GET', 'POST'))

# TODO(e-carlin): sort
def _validate_root_redirect_uris(uri_to_route, simulation_db):
    from sirepo import feature_config

    u = set(uri_to_route.keys())
    t = feature_config.cfg().sim_types
    r = set(simulation_db.SCHEMA_COMMON.rootRedirectUri.keys())
    i = u & r | u & t | r & t
    assert not i, f'rootRedirectUri, sim_types, and routes have overlapping uris={i}'
    for x in r:
        assert re.search(r'^[a-z]+$', x), \
            f'rootRedirectUri={x} must consist of letters only'



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
    in_optional = None
    in_path_info = None
    first = None
    for p in parts:
        assert not in_path_info, \
            'path_info parameter={} must be last: next={}'.format(rp.name, p)
        m = _PARAM_RE.search(p)
        if not m:
            assert first is None, \
                'too many non-parameter components of uri={}'.format(uri)
            first = p
            continue
        rp = pkcollections.Dict()
        params.append(rp)
        rp.is_optional = bool(m.group(1))
        if rp.is_optional:
            rp.is_path_info = m.group(1) == _PATH_INFO_CHAR
            in_path_info = rp.is_path_info
        else:
            rp.is_path_info = False
        rp.name = m.group(2)
        if rp.is_optional:
            in_optional = True
        else:
            assert not in_optional, \
                '{}: optional parameter ({}) followed by non-optional'.format(
                    uri,
                    rp.name,
                )
    res.base_uri = first or ''
    return res
