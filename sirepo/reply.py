# -*- coding: utf-8 -*-
"""Reply hold the response to API calls.

Replies are independent of the web platform (tornado or flask). They
are converted to the native format by the platform dispatcher at the
time. Internal call_api returns an `_SReply` object.

:copyright: Copyright (c) 2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html

"""
from pykern import pkcompat
from pykern import pkconfig
from pykern import pkconst
from pykern import pkio
from pykern import pkjinja
from pykern import pkjson
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp
import email.utils
import mimetypes
import pykern.pkinspect
import re
import sirepo.const
import sirepo.html
import sirepo.resource
import sirepo.uri
import sirepo.util

#: data.state for srException
SR_EXCEPTION_STATE = "srException"

#: mapping of extension (json, js, html) to MIME type
_MIME_TYPE = None

_MIME_TYPE_UTF8 = None

#: default Max-Age header
CACHE_MAX_AGE = 43200

ERROR_STATE = "error"

STATE = "state"

#: Default response
_RESPONSE_OK = PKDict({STATE: "ok"})

#: routes that will require a reload
_RELOAD_JS_ROUTES = None

_DISPOSITION = "Content-Disposition"


def init_module(**imports):
    global _MIME_TYPE, _MIME_TYPE_UTF8, _RELOAD_JS_ROUTES

    if _MIME_TYPE:
        return

    # import simulation_db
    sirepo.util.setattr_imports(imports)
    _MIME_TYPE = PKDict(
        html="text/html",
        ipynb="application/x-ipynb+json",
        js="application/javascript",
        json="application/json",
        madx="text/plain",
        py="text/x-python",
        txt="text/plain",
    )
    _MIME_TYPE_UTF8 = frozenset(_MIME_TYPE.values())
    s = simulation_db.get_schema(sim_type=None)
    _RELOAD_JS_ROUTES = frozenset(
        (k for k, v in s.localRoutes.items() if v.get("requireReload")),
    )


def init_quest(qcall):
    qcall.attr_set("sreply", _SReply(qcall=qcall))


class _SReply(sirepo.quest.Attr):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Needed in tornado_response, after _SRequest is destroyed
        self.internal_req = self.qcall.sreq.internal_req
        self._cookies_to_delete = None

    def content_as_str(
        self,
    ):
        res = self.__attrs.get("content")
        if res is None:
            return ""
        if isinstance(res, PKDict):
            res = res.read()
        return pkcompat.from_bytes(res)

    def cookie_set(self, **kwargs):
        assert "key" in kwargs
        assert "value" in kwargs
        self.__attrs.cookie = PKDict(kwargs)
        return self

    def delete_third_party_cookies(self, names_and_paths):
        if self._cookies_to_delete is not None:
            raise AssertionError(
                f"setting names_and_paths={names_and_paths} but found existing _cookies_to_delete={self._cookies_to_delete}"
            )
        self._cookies_to_delete = names_and_paths

    def destroy(self, **kwargs):
        """Must be called"""
        try:
            self.__attrs.pknested_get("content.handle").close()
            self.__attrs.content.pkdel("handle")
        except Exception:
            pass

    def flask_response(self, cls):
        from werkzeug import utils
        from flask import request

        def _cache_control(resp):
            if "cache" not in self.__attrs:
                return resp
            c = self.__attrs.cache
            if c.cache:
                resp.cache_control.max_age = CACHE_MAX_AGE
                resp.headers["Cache-Control"] = "private, max-age=43200"
                if c.mtime is not None:
                    resp.headers["Last-Modified"] = email.utils.formatdate(
                        c.mtime,
                        usegmt=True,
                    )
            else:
                resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
                resp.headers["Pragma"] = "no-cache"
            return resp

        def _delete_cookies(resp):
            for n, p in self.pkdel(self._cookies_to_delete) or ():
                resp.delete_cookie(
                    n,
                    path=p,
                )

        def _file():
            # Takes over some of the work for werkzeug.send_file
            c = self.__attrs.content
            res = utils.send_file(
                c.handle,
                environ=request.environ,
                mimetype=self.__attrs.content_type,
                download_name=a.download_name,
                last_modified=c.mtime,
            )
            c.pkdel("handle")
            res.headers["Content-Encoding"] = c.encoding
            res.content_length = c.length
            return res

        a = self.__attrs
        c = a.get("content", "")
        if isinstance(c, PKDict):
            r = _file()
        else:
            r = cls(
                response=c,
                mimetype=a.get("content_type"),
                status=a.get("status"),
            )
        r.headers.update(a.headers)
        if "cookie" in a and 200 <= r.status_code < 400:
            r.set_cookie(**a.cookie)
            _delete_cookies(r)
        return _cache_control(r)

    def from_api(self, res):
        """Process the reply of a call to another API

        Destructively copies `res` to `self` if res is an`_SReply`
        """
        if isinstance(res, _SReply):
            return self._copy(res)
        if isinstance(res, dict):
            return self.gen_json(res)
        raise AssertionError(f"invalid return type={type(res)} from qcall={self.qcall}")

    def from_kwargs(self, **kwargs):
        """Saves reply attributes

        While replies are global (qcall.sreply), the attributes need
        to be reset every time a new reply is generated.
        """
        self.destroy()
        self.__attrs = PKDict(kwargs).pksetdefault(headers=PKDict)
        return self

    def gen_exception(self, exc):
        """Generate from an Exception

        Args:
            exc (Exception): valid convert into a response
        """
        # If an exception occurs here, we'll fall through
        # to the server, which will have code to handle this case.
        if isinstance(exc, sirepo.util.ReplyExc):
            return self._gen_exception_reply(exc)
        return self._gen_exception_error(exc)

    def gen_file(self, path, content_type, filename):
        def _open():
            if self.qcall.sreq.is_websocket() and content_type in _MIME_TYPE_UTF8:
                return pkio.open_text(path)
            return open(path, "rb")

        # Always (re-)initialize __attrs
        self.from_kwargs()
        try:
            e = None
            if content_type is None:
                content_type, e = self._guess_content_type(path.basename)
            self._download_name(filename or path.basename)
            self.__attrs.content_type = content_type
            self.__attrs.content = PKDict(
                encoding=e,
                length=path.size(),
                mtime=int(path.mtime()),
                path=path,
            )
            # Need a handle, because path may get deleted before response.
            # Here to avoid unclosed handles on exceptions.
            self.__attrs.content.handle = _open()
            return self
        except Exception:
            self.__attrs.pkdel("content")
            self.__attrs.pkdel("content_type")
            self.__attrs.pkdel("download_name")
            raise

    def gen_file_as_attachment(self, content_or_path, filename=None, content_type=None):
        """Generate a file attachment response

        Args:
            content_or_path (bytes or py.path): File contents
            filename (str): Name of file [content_or_path.basename]
            content_type (str): MIMETYPE of file [guessed]

        Returns:
            _SReply: reply object
        """

        def _reply(filename):
            if isinstance(content_or_path, pkconst.PY_PATH_LOCAL_TYPE):
                return self.gen_file(
                    path=content_or_path,
                    content_type=content_type,
                    filename=filename,
                )
            if content_type == "application/json":
                self.from_kwargs(
                    content=pkjson.dump_pretty(content_or_path, pretty=False),
                    content_type=content_type,
                )
            else:
                self.from_kwargs(
                    content=content_or_path,
                    content_type=content_type or self._guess_content_type(filename)[0],
                )
            self._download_name(filename)
            return self

        return _reply(filename)._disposition("attachment").headers_for_no_cache()

    def gen_json(self, value, response_kwargs=None):
        """Generate JSON response

        Args:
            value (dict): what to format
        Returns:
            _SReply: reply object
        """
        if not response_kwargs:
            response_kwargs = PKDict()
        return self.from_kwargs(
            content=simulation_db.generate_json(value, pretty=False),
            content_type=_MIME_TYPE.json,
            **response_kwargs,
        )

    def gen_json_ok(self, *args, **kwargs):
        """Generate state=ok JSON response

        Returns:
            _SReply: reply object
        """
        if not args:
            # do not cache this, see #1390
            return self.gen_json(_RESPONSE_OK)
        assert len(args) == 1
        res = args[0]
        res.update(_RESPONSE_OK)
        return self.gen_json(res)

    def gen_redirect(self, uri):
        """Redirect to uri

        Args:
            uri (str): any valid uri (even with anchor)
        Returns:
            _SReply: reply object
        """
        return self.gen_redirect_for_anchor(uri)

    def gen_redirect_for_anchor(self, uri, **kwargs):
        """Redirect uri with an anchor using javascript

        Safari browser doesn't support redirects with anchors so we do this
        in all cases. It also allows us to return sr_exception to the app
        when we don't know if we can.

        Args:
            uri (str): where to redirect to
        Returns:
            _SReply: reply object
        """
        return self.render_static_jinja(
            "javascript-redirect",
            "html",
            PKDict(redirect_uri=uri, **kwargs),
        )

    def gen_redirect_for_local_route(
        self,
        sim_type=None,
        route=None,
        params=None,
        query=None,
        **kwargs,
    ):
        """Generate a javascript redirect to sim_type/route/params

        Default route (None) only supported for ``default``
        application_mode/appMode.

        Args:
            sim_type (str): how to find the schema [qcall.sim_type]
            route (str): name in localRoutes [None: use default route]
            params (dict): parameters for route (including :Name)

        Returns:
            _SReply: reply object
        """
        return self.gen_redirect_for_anchor(
            sirepo.uri.local_route(
                self.qcall.sim_type_uget(sim_type), route, params, query
            ),
            **kwargs,
        )

    def header_set(self, name, value):
        self.__attrs.headers[name] = value
        return self

    def headers_for_cache(self, path=None):
        self.__attrs.cache = PKDict(cache=True, mtime=path and path.mtime())
        return self

    def headers_for_no_cache(self):
        self.__attrs.cache = PKDict(cache=False)
        return self

    def init_child(self, qcall):
        """Initialize child from parent (self)"""
        # nothing to do with parent
        init_quest(qcall)

    def render_html(self, path, want_cache=True, attrs=None):
        """Call sirepo.html.render with path

        Args:
            path (py.path): sirepo.html file to render
            want_cache (bool): whether to cache result
            kwargs (dict): params to p

        Returns:
            _SReply: reply
        """
        r = self.from_kwargs(
            content=sirepo.html.render(path),
            content_type=_MIME_TYPE.html,
            **(attrs or PKDict()),
        )
        return (
            r.headers_for_cache(path=path) if want_cache else r.headers_for_no_cache()
        )

    def render_static_jinja(self, base, ext, j2_ctx, cache_ok=False):
        """Render static template with jinja

        Args:
            base (str): base name of file, e.g. ``user-state``
            ext (str): suffix of file, e.g. ``js``
            j2_ctx (dict): jinja context
            cache_ok (bool): OK to cache the result? [default: False]

        Returns:
            _SReply: reply
        """
        p = sirepo.resource.static(ext, f"{base}.{ext}")
        r = self.from_kwargs(
            content=pkjinja.render_file(p, j2_ctx, strict_undefined=True),
            content_type=_MIME_TYPE[ext],
        )
        if cache_ok:
            return r.headers_for_cache(path=p)
        return r.headers_for_no_cache()

    def status_as_int(self):
        return self.__attrs.get("status", 200)

    def tornado_response(self):
        def _bytes(resp, content):
            c = pkcompat.to_bytes(content)
            resp.write(c)
            resp.set_header("Content-Length", str(len(c)))

        def _cache_control(resp):
            if "cache" not in self.__attrs:
                return resp
            c = self.__attrs.cache
            if c.cache:
                resp.set_header(
                    "Cache-Control",
                    f"private, max-age={CACHE_MAX_AGE}",
                )
                if c.mtime is not None:
                    resp.set_header(
                        "Last-Modified",
                        email.utils.formatdate(c.mtime, usegmt=True),
                    )
            else:
                resp.set_header("Cache-Control", "no-cache, no-store, must-revalidate")
                resp.set_header("Pragma", "no-cache")

        def _content_type(resp):
            c = a.content_type
            if c in _MIME_TYPE_UTF8:
                c += '; charset="utf8"'
            r.set_header("Content-Type", c)

        def _cookie(resp):
            # TODO(robnagler) http.cookies 3.8 introduced samesite and blows up otherwise.
            # we know how our cookies are formed so
            a = self.__attrs
            if not ("cookie" in a and 200 <= a.status < 400):
                return
            c = a.cookie
            r = [f'{c.pkdel("key")}={c.pkdel("value")}', "Path=/"]
            for k in sorted(c.keys()):
                if k == "httponly":
                    if c[k]:
                        r.append("HttpOnly")
                elif k == "max_age":
                    r.append(f"Max-Age={c[k]}")
                elif k == "samesite":
                    r.append(f"SameSite={c[k]}")
                elif k == "secure":
                    if c[k]:
                        r.append("Secure")
                else:
                    raise AssertionError(f"unhandled cookie attr={k}")
            resp.set_header("Set-Cookie", "; ".join(r))
            _cookie_aux_delete(resp)

        def _cookie_aux_delete(resp):
            for n, p in self.pkdel(self._cookies_to_delete) or ():
                resp.clear_cookie(
                    n,
                    path=p,
                )

        def _file(resp):
            a = self.__attrs
            c = a.content
            resp.write(c.handle.read())
            c.handle.close()
            c.pkdel("handle")
            if _DISPOSITION not in a.headers:
                self._disposition("inline")
            resp.set_header(
                "Last-Modified",
                email.utils.formatdate(c.mtime, usegmt=True),
            )
            if c.encoding:
                resp.set_header("Content-Encoding", c.encoding)
            resp.set_header("Content-Length", str(c.length))

        a = self.__attrs
        c = a.get("content")
        if c is None:
            c = b""
            a.content_type = _MIME_TYPE.txt
        r = self.internal_req
        a.pksetdefault(status=200)
        if isinstance(c, PKDict):
            _file(r)
        else:
            _bytes(r, c)
        r.set_status(a.status)
        for k, v in a.headers.items():
            r.set_header(k, v)
        _content_type(r)
        _cache_control(r)
        _cookie(r)
        return r

    async def websocket_response(self):
        import msgpack

        a = self.__attrs
        p = msgpack.Packer(autoreset=False)
        p.pack(
            PKDict(
                contentType=a.get("content_type", _MIME_TYPE.txt),
                httpStatus=a.get("status", 200),
                kind=sirepo.const.SCHEMA_COMMON.websocketMsg.kind.httpReply,
                reqSeq=self.internal_req.req_seq,
                version=sirepo.const.SCHEMA_COMMON.websocketMsg.version,
            ),
        )
        c = a.get("content")
        if c is None:
            # always have content, easier for clients
            c = ""
        elif isinstance(c, PKDict):
            # TODO(robnagler) would be ideal to handle this differently, but
            # it may not be possible. Tornado/msgpack has lots of copying.
            x = c.handle.read()
            c.handle.close()
            c = x
        else:
            pass
        p.pack(c)
        # TODO(robnagler) getbuffer() would be better
        await self.internal_req.handler.write_message(p.bytes(), binary=True)
        p.reset()

    def _copy(self, source):
        """Destructive copy unless `self` is `res`"""
        if source == self:
            return self
        res = self.from_kwargs(**source.__attrs)
        # Destructive so "handle" not used by caller
        source.__attrs = None
        return res

    def _disposition(self, disposition):
        self.header_set(
            _DISPOSITION, f'{disposition}; filename="{self.__attrs.download_name}"'
        )
        return self

    def _download_name(self, filename):
        def _secure_filename():
            return re.sub(r"[^\w\.]+", "-", filename).strip("-")

        f = _secure_filename()
        if f.startswith("."):
            # the safe filename has no basename, prefix with "download"
            f = "download" + f
        self.__attrs.download_name = f

    def _gen_exception_error(self, exc):
        pkdlog("unsupported exception={} msg={}", type(exc), exc)
        if self.qcall.sreq.is_spider():
            return self.from_kwargs(
                content="""<!doctype html><html>
<head><title>500 Internal Server Error</title></head>
<body><h1>Internal Server Error</h1></body>
</html>
""",
                content_type=_MIME_TYPE.html,
                status=500,
            )
        return self.gen_redirect_for_local_route(None, route="error")

    def _gen_exception_base(self, exc):
        return self._gen_exception_reply(exc)

    def _gen_exception_reply(self, exc):
        f = getattr(
            self,
            "_gen_exception_reply_" + exc.__class__.__name__,
            None,
        )
        pkdc("exception={} sr_args={}", exc, exc.sr_args)
        if not f:
            return self._gen_exception_error(exc)
        return f(exc.sr_args)

    def _gen_exception_reply_BadRequest(self, args):
        return self._gen_http_exception(400)

    def _gen_exception_reply_ContentTooLarge(self, args):
        return self._gen_http_exception(413)

    def _gen_exception_reply_Error(self, args):
        try:
            t = qcall.sim_type_uget(args.pkdel("sim_type"))
            s = simulation_db.get_schema(sim_type=t)
        except Exception:
            # sim_type is bad so don't cascade errors, just
            # try to get the schema without the type
            t = None
            s = simulation_db.get_schema(sim_type=None)
        if self.qcall.sreq.method_is_post():
            return self.gen_json(args.pkupdate({STATE: ERROR_STATE}))
        q = PKDict()
        for k, v in args.items():
            try:
                v = str(v)
                assert len(v) < 200, "value is too long (>=200 chars)"
            except Exception as e:
                pkdlog('error in "error" query {}={} exception={}', k, v, e)
                continue
            q[k] = v
        return self.gen_redirect_for_local_route(t, route="error", query=q)

    def _gen_exception_reply_Forbidden(self, args):
        return self._gen_http_exception(403)

    def _gen_exception_reply_NotFound(self, args):
        return self._gen_http_exception(404)

    def _gen_exception_reply_Redirect(self, args):
        return self.gen_redirect(args.uri)

    def _gen_exception_reply_SReplyExc(self, args):
        r = args.sreply
        if not isinstance(r, _SReply):
            raise AssertionError(f"invalid class={type(r)} response={r}")
        return self._copy(r)

    def _gen_exception_reply_ServerError(self, args):
        return self._gen_http_exception(500)

    def _gen_exception_reply_SPathNotFound(self, args):
        pkdlog("uncaught SPathNotFound {}", args)
        return self.from_kwargs(
            content="""<!doctype html><html>
<head><title>404 Not Found</title></head>
<body><h1>Not Found</h1></body>
</html>
""",
            content_type=_MIME_TYPE.html,
            status=404,
        )

    def _gen_exception_reply_SRException(self, args):
        r = args.routeName
        p = args.params or PKDict()
        try:
            t = self.qcall.sim_type_uget(p.pkdel("sim_type"))
            s = simulation_db.get_schema(sim_type=t)
        except Exception as e:
            pkdc("exception={} stack={}", e, pkdexc())
            # sim_type is bad so don't cascade errors, just
            # try to get the schema without the type
            t = None
            s = simulation_db.get_schema(sim_type=None)
        # If default route or always redirect/reload
        if r:
            assert (
                r in s.localRoutes
            ), "route={} not found in schema for type={}".format(r, t)
        else:
            r = sirepo.uri.default_local_route_name(s)
            p = PKDict(reload_js=True)
        if (
            # must be first, to always delete reload_js
            not p.pkdel("reload_js")
            and self.qcall.sreq.method_is_post()
            and r not in _RELOAD_JS_ROUTES
        ):
            pkdc("POST response={} route={} params={}", SR_EXCEPTION_STATE, r, p)
            return self.gen_json(
                PKDict(
                    {
                        STATE: SR_EXCEPTION_STATE,
                        SR_EXCEPTION_STATE: args,
                    }
                ),
            )
        pkdc("redirect to route={} params={} type={}", r, p, t)
        return self.gen_redirect_for_local_route(
            t,
            route=r,
            params=p,
            sr_exception=pkjson.dump_pretty(args, pretty=False),
        )

    def _gen_exception_reply_Unauthorized(self, args):
        return self._gen_http_exception(401)

    def _gen_exception_reply_UserDirNotFound(self, args):
        return self.qcall.auth.user_dir_not_found(**args)

    def _gen_exception_reply_UserAlert(self, args):
        return self.gen_json(
            PKDict({STATE: ERROR_STATE, ERROR_STATE: args.error}),
        )

    def _gen_exception_reply_WWWAuthenticate(self, args):
        return self.from_kwargs(
            status=401,
        ).header_set("WWW-Authenticate", 'Basic realm="*"')

    def _gen_http_exception(self, code):
        x = simulation_db.SCHEMA_COMMON["customErrors"].get(str(code))
        if x:
            try:
                return self.render_html(
                    path=sirepo.resource.static("html", x["url"]),
                    want_cache=False,
                    attrs=PKDict(status=code),
                )
            except Exception as e:
                pkdlog(
                    "customErrors code={} render error={} stack={}", code, e, pkdexc()
                )
        # If there isn't a customError, then render empty reponse
        return self.from_kwargs(status=code).headers_for_no_cache()

    def _guess_content_type(self, basename):
        res = mimetypes.guess_type(basename)
        if res[0] is None:
            return "application/octet-stream", None
        # overrule mimetypes for this case
        elif res[0] == "text/x-python":
            return "text/plain", res[1]
        return res
