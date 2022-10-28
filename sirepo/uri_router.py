# -*- coding: utf-8 -*-
"""Handles dispatching of uris to server.api_* functions

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern import pkinspect
from pykern import pkconfig
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp
import contextlib
import importlib
import inspect
import os
import pkgutil
import re
import sirepo.api_auth
import sirepo.auth
import sirepo.cookie
import sirepo.events
import sirepo.feature_config
import sirepo.http_reply
import sirepo.http_request
import sirepo.quest
import sirepo.sim_api
import sirepo.uri
import sirepo.util

#: route for sirepo.srunit
srunit_uri = None

#: prefix for api functions
_FUNC_PREFIX = "api_"

#: modules that must be initialized
_REQUIRED_MODULES = ("auth_api", "job_api", "server", "srtime")

#: uri for default dispatches
_ROUTE_URI_DEFAULT = ""

#: uri for not found dispatches
_ROUTE_URI_NOT_FOUND = "not-found"

#: Where to route when no routes match (root)
_route_default = None

#: Where to route when no routes match (root)
_route_default = None

#: Where to route when a route is not found (notFound)
_route_default = None

#: dict of base_uri to route (base_uri, func, name, decl_uri, params)
_uri_to_route = None

#: dict of base_uri to route (base_uri, func, name, decl_uri, params)
_api_to_route = None

#: modules which support APIs
_api_modules = []

#: functions which implement APIs
_api_funcs = PKDict()

_init_for_flask = None


def assert_api_name_and_auth(qcall, name, allowed):
    """Check if `name` is executable and in allowed

    Args:
        qcall (sirepo.quest.API)
        name (str): name of the api
        allowed (tuple): names that are allowed to be called
    Returns:
        str: api name
    """
    _check_route(qcall, _api_to_route[name])
    if name not in allowed:
        raise AssertionError(f"api={name} not in allowed={allowed}")


def call_api(qcall, name, kwargs=None, data=None):
    """Should not be called outside of Base.call_api(). Use self.call_api() to call API.

    Call another API with permission checks.

    Note: also calls `save_to_cookie`.

    Args:
        qcall (quest.API): request object
        route_or_name (object): api function or name (without `api_` prefix)
        kwargs (dict): to be passed to API [None]
        data (dict): will be returned `qcall.parse_json`
    Returns:
        Response: result
    """
    return _call_api(qcall, _api_to_route[name], kwargs=kwargs, data=data)


def init_for_flask(app):
    """and adds a single flask route (`_dispatch`) to dispatch based on the map."""
    global _init_for_flask

    if _init_for_flask:
        return
    _init_for_flask = True
    app.add_url_rule("/<path:path>", "_dispatch", _dispatch, methods=("GET", "POST"))
    app.add_url_rule("/", "_dispatch_empty", _dispatch_empty, methods=("GET", "POST"))


def init_module(want_apis, **imports):
    """Convert route map to dispatchable callables

    Initializes `_uri_to_route`
    """
    global _uri_to_route

    def _api_modules():
        m = (
            *_REQUIRED_MODULES,
            *sorted(sirepo.feature_config.cfg().api_modules),
        )
        if sirepo.feature_config.cfg().moderated_sim_types:
            return m + ("auth_role_moderation",)
        return m

    if _uri_to_route is not None:
        return
    # import simulation_db
    sirepo.util.setattr_imports(imports)
    if not want_apis:
        _uri_to_route = PKDict()
        return
    for n in _api_modules():
        register_api_module("sirepo." + n)
    _register_sim_api_modules()
    _register_sim_oauth_modules(sirepo.feature_config.cfg().proprietary_oauth_sim_types)
    _init_uris(simulation_db, sirepo.feature_config.cfg().sim_types)


def maybe_sim_type_required_for_api(qcall):
    return sirepo.api_auth.maybe_sim_type_required_for_api(qcall.uri_route.func)


def register_api_module(module):
    """Add caller_module to the list of modules which implements apis.

    The module must have methods: api_XXX which do not collide with
    other apis. It may also have init_apis(), which will be called unless
    it is already registered.

    Args:
        module (module or str): name of module or module
    """

    def _is_api_func(cls, name, obj):
        return (
            name.startswith(_FUNC_PREFIX)
            and inspect.isfunction(obj)
            and name in cls.__dict__
        )

    assert (
        not _route_default
    ), "_init_uris already called. All APIs must registered at init"
    m = importlib.import_module(module) if isinstance(module, str) else module
    if m in _api_modules:
        return
    # prevent recursion
    _api_modules.append(m)
    if hasattr(m, "init_apis"):
        m.init_apis(uri_router=pkinspect.this_module())
    if not hasattr(m, "API"):
        if pkinspect.module_functions("api_", module=m):
            raise AssertionError(f"module={m.__name__} has old interface")
        pkdlog("module={} does not have API class; no apis", m)
        # some modules (ex: sirepo.auth.basic) don't have any APIs
        return
    c = m.API
    for n, o in inspect.getmembers(c):
        if _is_api_func(cls=c, name=n, obj=o):
            assert (
                not n in _api_funcs
            ), "function is duplicate: func={} module={}".format(n, m.__name__)
            _api_funcs[n] = _Route(func=o, cls=c, func_name=n)


def uri_for_api(api_name, params=None):
    """Generate uri for api method

    Args:
        api_name (str): full name of api
        params (PKDict): paramters to pass to uri
    Returns:
        str: formatted URI
    """
    if params is None:
        params = PKDict()
    r = _api_to_route[api_name]
    s = "/"
    res = (s + r.base_uri).rstrip("/")
    for p in r.params:
        if p.name in params:
            v = params[p.name]
            if not v is None and len(v) > 0:
                if not (p.is_path_info and v.startswith("/")):
                    res += "/"
                res += v
                continue
        assert p.is_optional, "missing parameter={} for api={}".format(p.name, api_name)
    return res or "/"


class _Route(sirepo.quest.Attr):
    """Holds all route information for an API.

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
    """Holds parameters for URI.

    Keys:
        is_optional (bool): is parameter optional
        is_path_info (bool): is parameter path info
        name (str): parameter name
    """

    pass


def _call_api(parent, route, kwargs, data=None):
    import werkzeug.exceptions

    def _response(res):
        if isinstance(res, dict):
            return sirepo.http_reply.gen_json(res)
        if res is None or isinstance(res, (str, tuple)):
            raise AssertionError("invalid return from qcall={}", qcall)
        return sirepo.http_reply.gen_response(res)

    qcall = route.cls()
    try:
        if parent:
            qcall.parent_set(parent)
        # POSIT: sirepo.quest does not copy this attr in parent_set
        qcall.attr_set("uri_route", route)
        qcall.sim_type_set_from_spec(route.func)
        if not parent:
            sirepo.auth.init_quest(qcall)
        if data:
            qcall.http_data_set(data)
        try:
            # must be first so exceptions have access to sim_type
            if kwargs:
                # Any (GET) uri will have simulation_type in uri if it is application
                # specific.
                qcall.sim_type_set(kwargs.get("simulation_type"))
            elif kwargs is None:
                kwargs = PKDict()
            _check_route(qcall, qcall.uri_route)
            r = _response(getattr(qcall, qcall.uri_route.func_name)(**kwargs))
        except Exception as e:
            if isinstance(e, (sirepo.util.Reply, werkzeug.exceptions.HTTPException)):
                pkdc("api={} exception={} stack={}", qcall.uri_route.name, e, pkdexc())
            else:
                pkdlog(
                    "api={} exception={} stack={}", qcall.uri_route.name, e, pkdexc()
                )
            r = sirepo.http_reply.gen_exception(qcall, e)
        sirepo.events.emit(qcall, "end_api_call", PKDict(resp=r))
        if pkconfig.channel_in("dev"):
            r.headers.add("Access-Control-Allow-Origin", "*")
        return r
    finally:
        qcall.destroy()


def _check_route(qcall, route):
    """Check if the route is authorized

    Args:
        route (_Route): API to check
    """
    sirepo.api_auth.check_api_call(qcall, route.func)


def _dispatch(path):
    """Called by Flask and routes the base_uri with parameters

    Args:
        path (str): what to route

    Returns:
        response
    """
    error, route, kwargs = _path_to_route(path)
    if error:
        pkdlog("path={} {}; route={} kwargs={} ", path, error, route, kwargs)
        route = _not_found_route

    return _call_api(None, route, kwargs=kwargs)


def _dispatch_empty():
    """Hook for '/' route"""
    return _dispatch(None)


def _init_uris(simulation_db, sim_types):
    global _route_default, _not_found_route, srunit_uri, _api_to_route, _uri_to_route

    assert not _route_default, "_init_uris called twice"
    _uri_to_route = PKDict()
    _api_to_route = PKDict()
    for k, v in simulation_db.SCHEMA_COMMON.route.items():
        r = _Route(_split_uri(v))
        try:
            r.update(_api_funcs[_FUNC_PREFIX + k])
        except KeyError:
            pkdc("not adding api, because module not registered: uri={}", v)
            continue
        sirepo.api_auth.assert_api_def(r.func)
        r.decl_uri = v
        r.name = k
        assert (
            not r.base_uri in _uri_to_route
        ), "{}: duplicate end point; other={}".format(v, _uri_to_route[r.base_uri])
        _uri_to_route[r.base_uri] = r
        _api_to_route[k] = r
        if r.base_uri == _ROUTE_URI_DEFAULT:
            _route_default = r
        elif r.base_uri == _ROUTE_URI_NOT_FOUND:
            _not_found_route = r
        elif "srunit" in v:
            srunit_uri = v
    assert _route_default, f"missing constant route: default /{_ROUTE_URI_DEFAULT}"
    assert (
        _not_found_route
    ), f"missing constant route: not found /{_ROUTE_URI_NOT_FOUND}"
    _validate_root_redirect_uris(_uri_to_route, simulation_db)


def _path_to_route(path):
    if path is None:
        return (None, _route_default, PKDict(path_info=None))
    parts = re.sub(r"\+", " ", path).split("/")
    route = None
    kwargs = None
    try:
        try:
            route = _uri_to_route[parts[0]]
            parts.pop(0)
        except KeyError:
            # Get here if the first part of the uri doesn't match a
            # route (all routes have only top level uris). It's likely
            # to be a sim_type, but could be other top level route items.
            # There should be no other parts so /foo/bar is going to yield
            # "too many parts" below.
            route = _route_default
        kwargs = PKDict()
        for p in route.params:
            if not parts:
                if not p.is_optional:
                    return (f"missing parameter={p.name}", route, kwargs)
                break
            if p.is_path_info:
                kwargs[p.name] = "/".join(parts)
                parts = None
                break
            kwargs[p.name] = parts.pop(0)
        if parts:
            return (f"has too many parts={parts}", route, kwargs)
    except Exception as e:
        return (f"parse exception={e} stack={pkdexc()}", route, kwargs)
    return (None, route, kwargs)


def _register_sim_api_modules():
    _register_sim_modules_from_package("sim_api")


def _register_sim_modules_from_package(package, valid_sim_types=None):
    for _, n, ispkg in pkgutil.iter_modules(
        [os.path.dirname(importlib.import_module(f"sirepo.{package}").__file__)],
    ):
        if ispkg:
            continue
        if not sirepo.template.is_sim_type(n) or (
            valid_sim_types is not None and n not in valid_sim_types
        ):
            pkdc(f"not adding apis for unknown sim_type={n}")
            continue
        register_api_module(f"sirepo.{package}.{n}")


def _register_sim_oauth_modules(oauth_sim_types):
    _register_sim_modules_from_package("sim_oauth", oauth_sim_types)


def _split_uri(uri):
    """Parse the URL for parameters

    Args:
        uri (str): full path with parameter args in uri format

    Returns:
        Dict: with base_uri, func, params, etc.
    """
    parts = uri.split("/")
    assert "" == parts.pop(0)
    params = []
    res = PKDict(params=params)
    in_optional = None
    in_path_info = None
    first = None
    for p in parts:
        assert not in_path_info, "path_info parameter={} must be last: next={}".format(
            rp.name, p
        )
        m = re.search(f"^{sirepo.uri.PARAM_RE.format('(.+?)')}$", p)
        if not m:
            assert first is None, "too many non-parameter components of uri={}".format(
                uri
            )
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
            assert (
                not in_optional
            ), "{}: optional parameter ({}) followed by non-optional".format(
                uri,
                rp.name,
            )
    res.base_uri = first or ""
    return res


def _validate_root_redirect_uris(uri_to_route, simulation_db):
    u = set(uri_to_route.keys())
    t = sirepo.feature_config.cfg().sim_types
    r = set(simulation_db.SCHEMA_COMMON.rootRedirectUri.keys())
    i = u & r | u & t | r & t
    assert not i, f"rootRedirectUri, sim_types, and routes have overlapping uris={i}"
    for x in r:
        assert re.search(
            r"^[a-z]+$", x
        ), f"rootRedirectUri={x} must consist of letters only"
