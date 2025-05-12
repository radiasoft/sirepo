"""Handles dispatching of uris to server.api_* functions

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern import pkcollections
from pykern import pkconfig
from pykern import pkinspect
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp, pkdformat
import asyncio
import importlib
import inspect
import re
import sirepo.api_auth
import sirepo.auth
import sirepo.const
import sirepo.events
import sirepo.feature_config
import sirepo.http_util
import sirepo.spa_session
import sirepo.uri
import sirepo.util

#: prefix for api functions
_FUNC_PREFIX = "api_"

#: modules that must be initialized
_REQUIRED_MODULES = ("auth_api", "job_api", "server", "srtime", "auth_role_moderation")

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

_BUCKET_KEY = "uri_route"


async def call_api(qcall, name, kwargs=None, body=None):
    """Should not be called outside of Base.call_api(). Use self.call_api() to call API.

    Call another API with permission checks.

    Args:
        qcall (quest.API): request object
        route_or_name (object): api function or name (without `api_` prefix)
        kwargs (PKDict): to be passed to API [None]
        body (PKDict): will be returned `qcall.body_as_dict`
    Returns:
        Response: result
    """
    return await _call_api(qcall, _api_to_route[name], kwargs=kwargs, body=body)


def init_module(want_apis, **imports):
    """Convert route map to dispatchable callables

    Initializes `_uri_to_route`
    """
    global _uri_to_route

    def _api_modules():
        return (
            *_REQUIRED_MODULES,
            *sorted(sirepo.feature_config.cfg().api_modules),
        )

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
    return sirepo.api_auth.maybe_sim_type_required_for_api(
        qcall.bucket_get(_BUCKET_KEY).func
    )


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
        if pkconfig.in_dev_mode():
            pkdlog(f"api_module={m.__name__} does not have API class (no apis)")
        # some modules (ex: sirepo.auth.basic) don't have any APIs
        return
    c = m.API
    for n, o in inspect.getmembers(c):
        if _is_api_func(cls=c, name=n, obj=o):
            assert (
                not n in _api_funcs
            ), "function is duplicate: func={} module={}".format(n, m.__name__)
            _api_funcs[n] = _Route(func=o, cls=c, func_name=n)


def start_tornado(ip, port, debug, is_primary=True):
    """Start tornado server, does not return"""
    from tornado import httpserver, ioloop, web, log, websocket

    ws_count = 0

    class _HTTPRequest(web.RequestHandler):
        async def _route(self):
            _log(self, "start")
            p = sirepo.uri.decode_to_str(self.request.path)
            e, r, k = _path_to_route(p[1:])
            if e:
                _log(
                    self,
                    "error",
                    fmt=" msg={} route={} kwargs={}",
                    args=[e, r, k],
                )
                r = _not_found_route
            await _call_api(
                None,
                r,
                kwargs=k,
                internal_req=self,
                reply_op=lambda r: r.tornado_response(self),
            )

        async def get(self):
            await self._route()

        async def post(self):
            await self._route()

        def sr_get_log_user(self):
            return getattr(self, "_sr_log_user", "")

        def sr_set_log_user(self, log_user):
            self._sr_log_user = log_user

    class _WebSocket(websocket.WebSocketHandler):
        async def get(self, *args, **kwargs):
            _log(self, "start")
            return await super().get(*args, **kwargs)

        async def on_message(self, msg):
            # WebSocketHandler only allows one on_message at a time.
            asyncio.ensure_future(self.__on_message(msg))

        def on_close(self):
            self.sr_log(
                None,
                "close",
                fmt=" code={} reason={}",
                args=[self.close_code, self.close_reason or ""],
            )

        def open(self):
            nonlocal ws_count

            # self.get_compression_options
            self.set_nodelay(True)
            r = self.request
            ws_count += 1
            self.__headers = PKDict(r.headers)
            self.cookie_state = self.__headers.get("Cookie")
            self.http_server_uri = f"{r.protocol}://{r.host}/"
            self.remote_addr = sirepo.http_util.remote_ip(r)
            self.ws_id = ws_count
            self.sr_log(None, "open", fmt=" ip={}", args=[_remote_peer(r)])

        def sr_get_log_user(self):
            """Needed for initial websocket creation call"""
            return ""

        def sr_log(self, ws_req, which, fmt="", args=None):
            pkdlog(
                "{} ws={}#{}" + fmt,
                which,
                self.ws_id,
                ws_req and ws_req.header.get("reqSeq") or 0,
                *args,
            )

        async def __on_message(self, msg):
            w = _WebSocketRequest(handler=self, headers=self.__headers)

            async def _reply_op(sreply):
                nonlocal w
                self.cookie_state = sreply.qcall.cookie.export_state()
                await sreply.websocket_response(w)

            try:
                w.parse_msg(msg)
                await _call_api(
                    None,
                    w.route,
                    kwargs=w.kwargs,
                    internal_req=w,
                    reply_op=_reply_op,
                )
            # TODO(robnagler) what if msg poorly constructed? Close socket?
            except Exception as e:
                self.sr_log(w, "error", fmt=" msg={} uri={}", args=[e, w.get("uri")])
                raise
            finally:
                self.sr_log(w, "end", fmt=" uid={}", args=[w.get("log_user")])

    class _WebSocketRequest(PKDict):
        def parse_msg(self, msg):
            import msgpack

            def _maybe_srunit_caller():
                if pkconfig.in_dev_mode() and (c := self.header.get("srunit_caller")):
                    return pkdformat(" srunit={}", c)
                return ""

            if not isinstance(msg, bytes):
                raise AssertionError(f"incoming msg type={type(msg)}")
            u = msgpack.Unpacker(
                max_buffer_size=sirepo.job.cfg().max_message_bytes,
                object_pairs_hook=pkcollections.object_pairs_hook,
            )
            u.feed(msg)
            self.header = u.unpack()
            self.handler.sr_log(
                self,
                "start",
                fmt=" uri={}{}",
                args=[self.header.get("uri"), _maybe_srunit_caller()],
            )
            if sirepo.const.SCHEMA_COMMON.websocketMsg.version != self.header.get(
                "version"
            ):
                raise AssertionError(
                    pkdformat("invalid header.version={}", self.header.get("version"))
                )
            # Ensures protocol conforms for all requests
            if (
                sirepo.const.SCHEMA_COMMON.websocketMsg.kind.httpRequest
                != self.header.get("kind")
            ):
                raise AssertionError(
                    pkdformat("invalid header.kind={}", self.header.get("kind"))
                )
            self.req_seq = self.header.reqSeq
            self.uri = self.header.uri
            if u.tell() < len(msg):
                self.body_as_dict = u.unpack()
                if u.tell() < len(msg):
                    self.attachment = u.unpack()
            # content may or may not exist so defer checking
            e, self.route, self.kwargs = _path_to_route(self.uri[1:])
            if e:
                self.handler.sr_log(
                    self,
                    "error",
                    fmt=" msg={} route={} kwargs={}",
                    args=[e, self.route, self.kwargs],
                )
                self.route = _not_found_route
            # Overwrite kwarg values if present in the message body
            if self.get("body_as_dict"):
                for k in self.body_as_dict:
                    if k in self.kwargs:
                        self.kwargs[k] = self.body_as_dict[k]

        def set_log_user(self, log_user):
            self.log_user = log_user

    def _cron_and_start():
        from sirepo import cron

        l = ioloop.IOLoop.current()
        cron.CronTask.init_class(l if is_primary else None)
        l.start()

    def _log(handler, which="end", fmt="", args=None):
        r = handler.request
        f = "{} ip={} uri={} "
        a = [which, _remote_peer(r), r.uri]
        if fmt:
            f += " " + fmt
            a += args
        elif which == "start":
            f += "proto={} {} ref={} ua={}"
            a += [
                r.method,
                r.version,
                r.headers.get("Referer") or "",
                r.headers.get("User-Agent") or "",
            ]
        else:
            f += "uid={} status={} ms={:.2f}"
            a += [
                handler.sr_get_log_user(),
                handler.get_status(),
                r.request_time() * 1000.0,
            ]
        pkdlog(f, *a)

    def _remote_peer(request):
        # https://github.com/tornadoweb/tornado/issues/2967#issuecomment-757370594
        # implementation may change; Code in tornado.httputil check connection.
        p = 0
        if c := request.connection:
            # socket is not set on stream for websockets.
            if hasattr(c, "stream") and hasattr(c.stream, "socket"):
                p = c.stream.socket.getpeername()[1]
        return f"{sirepo.http_util.remote_ip(request)}:{p}"

    sirepo.modules.import_and_init("sirepo.server").init_tornado()
    s = httpserver.HTTPServer(
        web.Application(
            [
                ("/ws", _WebSocket),
                ("/.*", _HTTPRequest),
            ],
            debug=debug,
            websocket_max_message_size=sirepo.job.cfg().max_message_bytes,
            websocket_ping_interval=sirepo.job.cfg().ping_interval_secs,
            websocket_ping_timeout=sirepo.job.cfg().ping_timeout_secs,
            log_function=_log,
        ),
        xheaders=True,
        max_buffer_size=sirepo.job.cfg().max_message_bytes,
    ).listen(port=port, address=ip)
    log.enable_pretty_logging()
    _cron_and_start()


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


class _Route(PKDict):
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


async def _call_api(parent, route, kwargs, body=None, internal_req=None, reply_op=None):
    qcall = route.cls()
    c = False
    r = None
    try:
        if parent:
            qcall.parent_set(parent)
        qcall.bucket_set(_BUCKET_KEY, route)
        qcall.sim_type_set_from_spec(route.func)
        if not parent:
            sirepo.auth.init_quest(qcall=qcall, internal_req=internal_req)
            await sirepo.spa_session.maybe_begin(qcall=qcall)
        if body is not None:
            qcall.sreq.set_body(body)
        try:
            # must be first so exceptions have access to sim_type
            if kwargs:
                # Any (GET) uri will have simulation_type in uri if it is application
                # specific.
                qcall.sim_type_set(kwargs.get("simulation_type"))
            elif kwargs is None:
                kwargs = PKDict()
            _check_route(qcall, route)
            r = qcall.sreply.uri_router_process_api_call(
                await getattr(qcall, route.func_name)(**kwargs)
            )
            c = True
        except Exception as e:
            if isinstance(e, sirepo.util.ReplyExc):
                if isinstance(e, sirepo.util.OKReplyExc):
                    c = True
                pkdc("api={} exception={} stack={}", route.name, e, pkdexc())
            else:
                pkdlog("api={} exception={} stack={}", route.name, e, pkdexc())
            qcall.cookie.has_sentinel()
            r = qcall.sreply.gen_exception(e)
        if parent:
            # Done with nested call. Detach since qcall destroyed below
            return r.detach_from_quest()
        sirepo.events.emit(qcall, "end_api_call", PKDict(resp=r))
        if pkconfig.in_dev_mode():
            r.header_set("Access-Control-Allow-Origin", "*")
        if inspect.iscoroutinefunction(reply_op):
            return await reply_op(r)
        else:
            return reply_op(r)
    except:
        c = False
        raise
    finally:
        qcall.destroy(commit=c)


def _check_route(qcall, route):
    """Check if the route is authorized

    Args:
        route (_Route): API to check
    """
    sirepo.api_auth.check_api_call(qcall, route.func)


def _init_uris(simulation_db, sim_types):
    global _route_default, _not_found_route, _api_to_route, _uri_to_route

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
    assert _route_default, f"missing constant route: default /{_ROUTE_URI_DEFAULT}"
    assert (
        _not_found_route
    ), f"missing constant route: not found /{_ROUTE_URI_NOT_FOUND}"
    _validate_root_redirect_uris(_uri_to_route, simulation_db)


def _path_to_route(path):
    if path is None:
        return (None, _route_default, PKDict(path_info=None))
    parts = path.split("/")
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
            return (pkdformat("has too many parts={}", parts), route, kwargs)
    except Exception as e:
        return (pkdformat("parse exception={} stack={}", e, pkdexc()), route, kwargs)
    return (None, route, kwargs)


def _register_sim_api_modules():
    _register_sim_modules_from_package("sim_api")


def _register_sim_modules_from_package(package, valid_sim_types=None):
    p = pkinspect.module_name_join(("sirepo", package))
    for n in pkinspect.package_module_names(p):
        if not sirepo.template.is_sim_type(n) or (
            valid_sim_types is not None and n not in valid_sim_types
        ):
            pkdc(f"not adding apis for unknown sim_type={n}")
            continue
        register_api_module(pkinspect.module_name_join((p, n)))


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
