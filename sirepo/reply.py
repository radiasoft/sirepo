# -*- coding: utf-8 -*-
"""Reply hold the response to API calls

:copyright: Copyright (c) 2022 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern import pkconfig
from pykern import pkconst
from pykern import pkio
from pykern import pkjinja
from pykern import pkjson
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp
import mimetypes
import pykern.pkinspect
import re
import sirepo.html
import sirepo.http_request
import sirepo.resource
import sirepo.uri
import sirepo.util

#: data.state for srException
SR_EXCEPTION_STATE = "srException"

#: mapping of extension (json, js, html) to MIME type
MIME_TYPE = None

#: default Max-Age header
CACHE_MAX_AGE = 43200

ERROR_STATE = "error"

STATE = "state"

#: Default response
_RESPONSE_OK = PKDict({_STATE: "ok"})

#: routes that will require a reload
_RELOAD_JS_ROUTES = None


def init_module(**imports):
    global MIME_TYPE, _RELOAD_JS_ROUTES

    if MIME_TYPE:
        return

    # import simulation_db
    sirepo.util.setattr_imports(imports)
    MIME_TYPE = PKDict(
        html="text/html",
        ipynb="application/x-ipynb+json",
        js="application/javascript",
        json="application/json",
        py="text/x-python",
        madx="text/plain",
    )
    s = simulation_db.get_schema(sim_type=None)
    _RELOAD_JS_ROUTES = frozenset(
        (k for k, v in s.localRoutes.items() if v.get("requireReload")),
    )


def init_quest(qcall):
    qcall.attr_set("sreply", _SReply(qcall=qcall))


class _SReply(sirepo.quest.Attr):
    def flask_response(self, cls):
        from werkzeug import utils

        def _cache(resp, cache):
            if isinstance(cache, bool):
                assert cache == False
                resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
                resp.headers["Pragma"] = "no-cache"
            else:
                resp.cache_control.max_age = CACHE_MAX_AGE
                if cache > 0:
                    resp.last_modified = path.mtime()
            return resp


            path_or_file=path_or_file,
            mimetype=a.content_type,
            conditional=True,
            last_modified=last_modified,
            max_age=max_age,
            cache_timeout=cache_timeout,

        return cls(
            response=_content(a),
            status=a.get("status", 200),
            a.headers=_headers(),
        )

    def gen_exception(self, exc):
        """Generate from an Exception

        Args:
            exc (Exception): valid convert into a response
        """
        # If an exception occurs here, we'll fall through
        # to the server, which will have code to handle this case.
        if isinstance(exc, sirepo.util.Reply):
            return self._gen_exception_reply(exc)
        return self._gen_exception_error(exc)

    def gen_file(self, path, content_type):
        e = None
        if content_type is None:
            content_type, e = self._guess_content_type(path.basename)
        self.__attrs.pkupdate(
            content_handle=open(path, "rb"),
            content_length=path.size(),
            content_mtime=int(path.mtime()),

        self.__attrs.content_length = path.size()
        self.

    return werkzeug.utils.send_file(
        **_prepare_send_file_kwargs(
            path_or_file=path_or_file,
            environ=request.environ,
            mimetype=mimetype,
            as_attachment=as_attachment,
            download_name=download_name,
            attachment_filename=attachment_filename,
            conditional=conditional,
            etag=etag,
            add_etags=add_etags,
            last_modified=last_modified,
            max_age=max_age,
            cache_timeout=cache_timeout,
        )
    )



        return self.gen_response(
            content_file=path,
            content_type=content_type,
        )

    def gen_file_as_attachment(self, content_or_path, filename=None, content_type=None):
        """Generate a file attachment response

        Args:
            content_or_path (bytes or py.path): File contents
            filename (str): Name of file [content_or_path.basename]
            content_type (str): MIMETYPE of file [guessed]

        Returns:
            _SReply: reply object
        """

        def f():
            if isinstance(content_or_path, pkconst.PY_PATH_LOCAL_TYPE):
                return self.gen_file(path=content_or_path, content_type=None)
            if content_type == "application/json":
                return self.gen_response(pkjson.dump_pretty(content_or_path))
            return self.gen_response(content=content_or_path)

        if filename is None:
            # dies if content_or_path is not a path
            filename = content_or_path.basename
        filename = re.sub(r"[^\w\.]+", "-", filename).strip("-")
        if re.search(r"^\.\w+$", filename):
            # the safe filename has no basename, prefix with "download"
            filename = "download" + filename
        return self.headers_for_no_cache(
            f()._as_attachment(
                content_type or self._guess_content_type(filename)[0],
                filename,
            ),
        )

    def gen_json(self, value, pretty=False, response_kwargs=None):
        """Generate JSON response

        Args:
            value (dict): what to format
            pretty (bool): pretty print [False]
        Returns:
            _SReply: reply object
        """
        if not response_kwargs:
            response_kwargs = PKDict()
        return self.gen_response(
            content=simulation_db.generate_json(value, pretty=pretty),
            content_type=MIME_TYPE.json,
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

    def gen_response(self, **kwargs):
        self.__attrs = PKDict(kwargs)
        return self

    def headers_for_cache(self, path=None):
        self.__attrs.cache = path and path.mtime()
        return self

    def headers_for_no_cache():
        self.__attrs.cache = False
        return self

    def render_html(path, want_cache=True, response_args=None):
        """Call sirepo.html.render with path

        Args:
            path (py.path): sirepo.html file to render
            want_cache (bool): whether to cache result
            kwargs (dict): params to p

        Returns:
            _SReply: reply
        """
        r = self.gen_response(
            content=sirepo.html.render(path),
            content_type=MIME_TYPE.html,
            **(response_args or PKDict()),
        )
        return (
            headers_for_cache(r, path=path) if want_cache else headers_for_no_cache(r)
        )

    def render_static_jinja(base, ext, j2_ctx, cache_ok=False):
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
        r = self.gen_response(
            content=pkjinja.render_file(p, j2_ctx, strict_undefined=True),
            content_type=MIME_TYPE[ext],
        )
        if cache_ok:
            return r.headers_for_cache(path=p)
        return r.headers_for_no_cache()

    def _as_attachment(self, content_type, filename):
        return self.__attrs.pkupdate(
            content_type=content_type,
            content_disposition=f'attachment; filename="{filename}"',
        )

    def _gen_exception_error(qcall, exc):
        pkdlog("unsupported exception={} msg={}", type(exc), exc)
        if qcall.sreq.is_spider():
            return gen_response(
                content="""<!doctype html><html>
<head><title>500 Internal Server Error</title></head>
<body><h1>Internal Server Error</h1></body>
</html>
""",
                content_type=MIME_TYPE.html,
                status=500,
            )
        return gen_redirect_for_local_route(qcall, None, route="error")

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

    def _gen_exception_reply_BadRequest(qcall, args):
        return _gen_http_exception(400)


    def _gen_exception_reply_Error(qcall, args):
        try:
            t = qcall.sim_type_uget(args.pkdel("sim_type"))
            s = simulation_db.get_schema(sim_type=t)
        except Exception:
            # sim_type is bad so don't cascade errors, just
            # try to get the schema without the type
            t = None
            s = simulation_db.get_schema(sim_type=None)
        if qcall.sreq.method_is_post():
            return gen_json(args.pkupdate({STATE: ERROR_STATE}))
        q = PKDict()
        for k, v in args.items():
            try:
                v = str(v)
                assert len(v) < 200, "value is too long (>=200 chars)"
            except Exception as e:
                pkdlog('error in "error" query {}={} exception={}', k, v, e)
                continue
            q[k] = v
        return gen_redirect_for_local_route(qcall, t, route="error", query=q)

    def _gen_exception_reply_Forbidden(qcall, args):
        return _gen_http_exception(403)

    def _gen_exception_reply_NotFound(qcall, args):
        return _gen_http_exception(404)

    def _gen_exception_reply_Redirect(qcall, args):
        return gen_redirect(args.uri)

    def _gen_exception_reply_SReply(self, args):
        r = args.sreply
        if not isinstance(r, _SReply):
            raise AssertionError(f"invalid class={type(r)} response={r}")
        return r

    def _gen_exception_reply_ServerError(qcall, args):
        return _gen_http_exception(500)

    def _gen_exception_reply_SPathNotFound(qcall, args):
        pkdlog("uncaught SPathNotFound {}", args)
        return gen_response(
            content="""<!doctype html><html>
<head><title>404 Not Found</title></head>
<body><h1>Not Found</h1></body>
</html>
""",
            content_type=MIME_TYPE.html,
            status=404,
        )

    def _gen_exception_reply_SRException(qcall, args):
        r = args.routeName
        p = args.params or PKDict()
        try:
            t = qcall.sim_type_uget(p.pkdel("sim_type"))
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
            and qcall.sreq.method_is_post()
            and r not in _RELOAD_JS_ROUTES
        ):
            pkdc("POST response={} route={} params={}", SR_EXCEPTION_STATE, r, p)
            return gen_json(
                PKDict(
                    {
                        _STATE: SR_EXCEPTION_STATE,
                        SR_EXCEPTION_STATE: args,
                    }
                ),
            )
        pkdc("redirect to route={} params={} type={}", r, p, t)
        return gen_redirect_for_local_route(
            qcall,
            t,
            route=r,
            params=p,
            sr_exception=pkjson.dump_pretty(args, pretty=False),
        )

    def _gen_exception_reply_Unauthorized(qcall, args):
        return _gen_http_exception(401)

    def _gen_exception_reply_UserDirNotFound(qcall, args):
        return qcall.auth.user_dir_not_found(**args)

    def _gen_exception_reply_UserAlert(qcall, args):
        return gen_json(
            PKDict({_STATE: ERROR_STATE, ERROR_STATE: args.error}),
        )

    def _gen_exception_reply_WWWAuthenticate(qcall, args):
        return gen_response(
            status=401,
            headers={"WWW-Authenticate": 'Basic realm="*"'},
        )

    def _gen_http_exception(code):
        x = simulation_db.SCHEMA_COMMON["customErrors"].get(str(code))
        if x:
            try:
                return render_html(
                    path=sirepo.resource.static("html", x["url"]),
                    want_cache=False,
                    response_args=PKDict(status=code),
                )
            except Exception as e:
                pkdlog(
                    "customErrors code={} render error={} stack={}", code, e, pkdexc()
                )
        # If there isn't a customError, then render empty reponse
        return self.gen_response(status=code).headers_for_no_cache()

    def _guess_content_type(basename):
        res = mimetypes.guess_type(basename)
        if res[0] is None:
            return "application/octet-stream", None
        # overrule mimetypes for this case
        elif res[0] == "text/x-python":
            return "text/plain", res[1]
        return res
