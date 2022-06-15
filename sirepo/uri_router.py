# -*- coding: utf-8 -*-
u"""Handles dispatching of uris to server.api_* functions

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern import pkinspect
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp
import contextlib
import flask
import importlib
import inspect
import os
import pkgutil
import re
import sirepo.api
import sirepo.api_auth
import sirepo.cookie
import sirepo.events
import sirepo.http_reply
import sirepo.http_request
import sirepo.sim_api
import sirepo.srcontext
import sirepo.uri
import sirepo.util
import werkzeug.exceptions


#: route for sirepo.srunit
srunit_uri = None

_API_ATTR = 'sirepo_uri_router_api'

#: prefix for api functions
_FUNC_PREFIX = 'api_'

#: modules that must be initialized. server must be first
_REQUIRED_MODULES = ('server', 'auth', 'srtime')

#: Where to route when no routes match (root)
_default_route = None

#: dict of base_uri to route (base_uri, func, name, decl_uri, params)
_uri_to_route = None

#: dict of base_uri to route (base_uri, func, name, decl_uri, params)
_api_to_route = None

#: modules which support APIs
_api_modules = []

#: functions which implement APIs
_api_funcs = PKDict()


def assert_api_name_and_auth(name, allowed):
    """Check if `name` is executable and in allowed

    Args:
        name (str): name of the api
        allowed (tuple): names that are allowed to be called
    Returns:
        str: api name
    """
    _check_api_call(name)
    if name not in allowed:
        raise AssertionError(f'api={name} not in allowed={allowed}')


def call_api(route_or_name, kwargs=None, data=None):
    """Should not be called outside of Base.call_api(). Use self.call_api() to call API.

    Call another API with permission checks.

    Note: also calls `save_to_cookie`.

    Args:
        route_or_name (object): api function or name (without `api_` prefix)
        kwargs (dict): to be passed to API [None]
        data (dict): will be returned `http_request.parse_json`
    Returns:
        flask.Response: result
    """
    p = None
    s = None
    with _set_api_attr(route_or_name):
        try:
            # must be first so exceptions have access to sim_type
            if kwargs:
                # Any (GET) uri will have simulation_type in uri if it is application
                # specific.
                s = sirepo.http_request.set_sim_type(kwargs.get('simulation_type'))
            else:
                kwargs = PKDict()
            f = _check_api_call(route_or_name)
            try:
                if data:
                    p = sirepo.http_request.set_post(data)
                r = flask.make_response(getattr(f.cls(), f.func_name)(**kwargs))
            finally:
                if data:
                    sirepo.http_request.set_post(p)
        except Exception as e:
            if isinstance(e, (sirepo.util.Reply, werkzeug.exceptions.HTTPException)):
                pkdc('api={} exception={} stack={}', route_or_name, e, pkdexc())
            else:
                pkdlog('api={} exception={} stack={}', route_or_name, e, pkdexc())
            r = sirepo.http_reply.gen_exception(e)
        finally:
            # http_request tries to keep a valid sim_type so
            # this is ok to call (even if s is None)
            sirepo.http_request.set_sim_type(s)
        sirepo.cookie.save_to_cookie(r)
        sirepo.events.emit('end_api_call', PKDict(resp=r))
        return r


def init(app, simulation_db):
    """Convert route map to dispatchable callables

    Initializes `_uri_to_route` and adds a single flask route (`_dispatch`) to
    dispatch based on the map.

    Args:
        app (Flask): flask app
    """
    def _api_modules():
        m = (
            *_REQUIRED_MODULES,
            *sorted(feature_config.cfg().api_modules),
        )
        if feature_config.cfg().moderated_sim_types:
            return m + ('auth_role_moderation',)
        return m

    if _uri_to_route:
        return

    from sirepo import feature_config

    for n in _api_modules():
        register_api_module(importlib.import_module('sirepo.' + n))
    _register_sim_api_modules()
    _register_sim_oauth_modules(feature_config.cfg().proprietary_oauth_sim_types)
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
    sirepo.api.init(
        http_reply=sirepo.http_reply,
        http_request=sirepo.http_request,
        uri_router=pkinspect.this_module(),
    )


def maybe_sim_type_required_for_api():
    a = sirepo.srcontext.get(_API_ATTR)
    if not a:
        return True
    return sirepo.api_auth.maybe_sim_type_required_for_api(a.func)


def register_api_module(module=None):
    """Add caller_module to the list of modules which implements apis.

    The module must have methods: api_XXX which do not collide with
    other apis. It may also have init_apis(), which will be called unless
    it is already registered.

    Args:
        module (module): defaults to caller module
    """
    def _is_api_func(cls, name, obj):
        return name.startswith(_FUNC_PREFIX) and inspect.isfunction(obj) and name in cls.__dict__

    assert not _default_route, \
        '_init_uris already called. All APIs must registered at init'
    m = module or pkinspect.caller_module()
    if m in _api_modules:
        return
    # prevent recursion
    _api_modules.append(m)
    if hasattr(m, 'init_apis'):
        m.init_apis()
    if not hasattr(m, 'API'):
        if pkinspect.module_functions('api_', module=m):
            raise AssertionError(f'module={m.__name__} has old interface')
        pkdlog('module={} does not have API class; no apis', m)
        # some modules (ex: sirepo.auth.basic) don't have any APIs
        return
    c = m.API
    for n, o in inspect.getmembers(c):
        if _is_api_func(cls=c, name=n, obj=o):
            assert not n in _api_funcs, \
                'function is duplicate: func={} module={}'.format(n, m.__name__)
            _api_funcs[n] = _Route(func=o, cls=c, func_name=n)


def uri_for_api(api_name, params=None, external=True):
    """Generate uri for api method

    Args:
        api_name (str): full name of api
        params (PKDict): paramters to pass to uri
        external (bool): if True, make the uri absolute [True]
    Returns:
        str: formmatted external URI
    """
    if params is None:
        params = PKDict()
    r = _api_to_route[api_name]
    s = flask.url_for('_dispatch_empty', _external=external) if external else '/'
    res = (s + r.base_uri).rstrip('/')
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
    return res or '/'


class _Route(PKDict):
    """ Holds all route information for an API.

    Keys:
        base_uri (str): first part of URI (ex: 'adjust-time')
        cls (class): The class in the API's module that contains the API function.
        decl_uri (str): full URI that's in schema (ex: '/adjust-time/?<days>')
        func (function): object that has api_perm attributes. should not be called as a function
        func_name (str): method name in cls that implements the route (ex: 'api_admJobs').
        name (str): API route name
        params (list): parameters for URI
    """
    pass

class _URIParams(PKDict):
    """ Holds parameters for URI.

    Keys:
        is_optional (bool): is parameter optional
        is_path_info (bool): is parameter path info
        name (str): parameter name
    """
    pass


def _check_api_call(route_or_name):
    """Check if API is callable by current user (proper credentials)

    Args:
        route_or_name (function or str): API to check
    """
    f = route_or_name if isinstance(route_or_name, _Route) \
        else _api_to_route[route_or_name]
    sirepo.api_auth.check_api_call(f.func)
    return f


def _dispatch(path):
    """Called by Flask and routes the base_uri with parameters

    Args:
        path (str): what to route

    Returns:
        Flask.response
    """
    import sirepo.auth

    with sirepo.auth.process_request():
        try:
            if path is None:
                return call_api(_default_route, PKDict(path_info=None))
            # werkzeug doesn't convert '+' to ' '
            parts = re.sub(r'\+', ' ', path).split('/')
            try:
                route = _uri_to_route[parts[0]]
                parts.pop(0)
            except KeyError:
                # sim_types (applications)
                route = _default_route
            kwargs = PKDict()
            for p in route.params:
                if not parts:
                    if not p.is_optional:
                        raise sirepo.util.raise_not_found('{}: uri missing parameter ({})', path, p.name)
                    break
                if p.is_path_info:
                    kwargs[p.name] = '/'.join(parts)
                    parts = None
                    break
                kwargs[p.name] = parts.pop(0)
            if parts:
                raise sirepo.util.raise_not_found('{}: unknown parameters in uri ({})', parts, path)
            return call_api(route, kwargs)
        except Exception as e:
            pkdlog('exception={} path={} stack={}', e, path, pkdexc())
            raise


def _dispatch_empty():
    """Hook for '/' route"""
    return _dispatch(None)


def _init_uris(app, simulation_db, sim_types):
    global _default_route, srunit_uri, _api_to_route, _uri_to_route

    assert not _default_route, \
        '_init_uris called twice'
    _uri_to_route = PKDict()
    _api_to_route = PKDict()
    for k, v in simulation_db.SCHEMA_COMMON.route.items():
        r = _Route(_split_uri(v))
        try:
            r.update(_api_funcs[_FUNC_PREFIX + k])
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
    _validate_root_redirect_uris(_uri_to_route, simulation_db)
    app.add_url_rule('/<path:path>', '_dispatch', _dispatch, methods=('GET', 'POST'))
    app.add_url_rule('/', '_dispatch_empty', _dispatch_empty, methods=('GET', 'POST'))


def _register_sim_api_modules():
    _register_sim_modules_from_package('sim_api')


def _register_sim_modules_from_package(package, valid_sim_types=None):
    for _, n, ispkg in pkgutil.iter_modules(
            [os.path.dirname(importlib.import_module(f'sirepo.{package}').__file__)],
    ):
        if ispkg:
            continue
        if not sirepo.template.is_sim_type(n) or \
                (valid_sim_types is not None and n not in valid_sim_types):
            pkdc(f'not adding apis for unknown sim_type={n}')
            continue
        register_api_module(importlib.import_module(f'sirepo.{package}.{n}'))

def _register_sim_oauth_modules(oauth_sim_types):
    _register_sim_modules_from_package('sim_oauth', oauth_sim_types)


@contextlib.contextmanager
def _set_api_attr(route_or_name):
    a = sirepo.srcontext.get(_API_ATTR)
    try:
        sirepo.srcontext.set(_API_ATTR, route_or_name)
        yield
    finally:
        sirepo.srcontext.set(_API_ATTR, a)


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
    res = PKDict(params=params)
    in_optional = None
    in_path_info = None
    first = None
    for p in parts:
        assert not in_path_info, \
            'path_info parameter={} must be last: next={}'.format(rp.name, p)
        m = re.search(f"^{sirepo.uri.PARAM_RE.format('(.+?)')}$", p)
        if not m:
            assert first is None, \
                'too many non-parameter components of uri={}'.format(uri)
            first = p
            continue
        rp = _URIParams()
        params.append(rp)
        rp.is_optional = bool(m.group(1))
        if rp.is_optional:
            rp.is_path_info = m.group(1) == sirepo.uri.PATH_INFO_CHAR
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
