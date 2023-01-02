# -*- coding: utf-8 -*-
"""response generation

:copyright: Copyright (c) 2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
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

#: Default file to serve on errors
DEFAULT_ERROR_FILE = "server-error.html"

_ERROR_STATE = "error"

_STATE = "state"

#: Default response
_RESPONSE_OK = PKDict({_STATE: "ok"})

#: Parsing errors from subprocess
_SUBPROCESS_ERROR_RE = re.compile(
    r"(?:warning|exception|error): ([^\n]+?)(?:;|\n|$)", flags=re.IGNORECASE
)

#: routes that will require a reload
_RELOAD_JS_ROUTES = None


def gen_exception(qcall, exc):
    """Generate from an Exception

    Args:
        exc (Exception): valid convert into a response
    """
    # If an exception occurs here, we'll fall through
    # to the server, which will have code to handle this case.
    if isinstance(exc, sirepo.util.Reply):
        return _gen_exception_reply(qcall, exc)
    return _gen_exception_error(qcall, exc)


def gen_file_as_attachment(qcall, content_or_path, filename=None, content_type=None):
    """Generate a file attachment response

    Args:
        content_or_path (bytes or py.path): File contents
        filename (str): Name of file [content_or_path.basename]
        content_type (str): MIMETYPE of file [guessed]

    Returns:
        Response: reply object
    """

    def f():
        if isinstance(content_or_path, pkconst.PY_PATH_LOCAL_TYPE):
            return qcall.reply_file(content_or_path)
        if content_type == "application/json":
            return gen_response(pkjson.dump_pretty(content_or_path))
        return gen_response(content_or_path)

    if filename is None:
        # dies if content_or_path is not a path
        filename = content_or_path.basename
    filename = re.sub(r"[^\w\.]+", "-", filename).strip("-")
    if re.search(r"^\.\w+$", filename):
        # the safe filename has no basename, prefix with "download"
        filename = "download" + filename
    return headers_for_no_cache(
        _as_attachment(
            f(),
            content_type or guess_content_type(filename),
            filename,
        ),
    )


def gen_json(value, pretty=False, response_kwargs=None):
    """Generate JSON response

    Args:
        value (dict): what to format
        pretty (bool): pretty print [False]
    Returns:
        Response: reply object
    """
    if not response_kwargs:
        response_kwargs = PKDict()
    return gen_response(
        simulation_db.generate_json(value, pretty=pretty),
        content_type=MIME_TYPE.json,
        **response_kwargs,
    )


def gen_json_ok(*args, **kwargs):
    """Generate state=ok JSON response

    Returns:
        Response: reply object
    """
    if not args:
        # do not cache this, see #1390
        return gen_json(_RESPONSE_OK)
    assert len(args) == 1
    res = args[0]
    res.update(_RESPONSE_OK)
    return gen_json(res)


def gen_redirect(uri):
    """Redirect to uri

    Args:
        uri (str): any valid uri (even with anchor)
    Returns:
        Response: reply object
    """
    return gen_redirect_for_anchor(uri)


def gen_redirect_for_anchor(uri, **kwargs):
    """Redirect uri with an anchor using javascript

    Safari browser doesn't support redirects with anchors so we do this
    in all cases. It also allows us to return sr_exception to the app
    when we don't know if we can.

    Args:
        uri (str): where to redirect to
    Returns:
        Response: reply object
    """
    return render_static_jinja(
        "javascript-redirect",
        "html",
        PKDict(redirect_uri=uri, **kwargs),
    )


def gen_redirect_for_local_route(
    qcall,
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
        qcall (request): request object
        sim_type (str): how to find the schema [qcall.sim_type]
        route (str): name in localRoutes [None: use default route]
        params (dict): parameters for route (including :Name)

    Returns:
        Response: reply object
    """
    return gen_redirect_for_anchor(
        sirepo.uri.local_route(qcall.sim_type_uget(sim_type), route, params, query),
        **kwargs,
    )


def gen_response(*args, **kwargs):
    if "content_type" in kwargs:
        kwargs["mimetype"] = kwargs["content_type"]
        del kwargs["content_type"]
    c = sirepo.flask.app().response_class
    if args and isinstance(args[0], c):
        assert len(args) == 1 and not kwargs
        return args[0]
    return c(*args, **kwargs)


def gen_tornado_exception(exc):
    if not isinstance(exc, sirepo.util.Reply):
        raise
    return getattr(
        pykern.pkinspect.this_module(),
        "_gen_tornado_exception_reply_" + exc.__class__.__name__,
    )(exc.sr_args)


def guess_content_type(basename):
    res, _ = mimetypes.guess_type(basename)
    if res is None:
        return "application/octet-stream"
    # overrule mimetypes for this case
    elif res == "text/x-python":
        return "text/plain"
    return res


def headers_for_cache(resp, path=None):
    resp.cache_control.max_age = CACHE_MAX_AGE
    if path:
        resp.last_modified = path.mtime()
    return resp


def headers_for_no_cache(resp):
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    resp.headers["Pragma"] = "no-cache"
    return resp


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


def render_html(path, want_cache=True, response_args=None):
    """Call sirepo.html.render with path

    Args:
        path (py.path): sirepo.html file to render
        want_cache (bool): whether to cache result
        kwargs (dict): params to p

    Returns:
        Response: reply
    """
    r = gen_response(
        sirepo.html.render(path),
        content_type=MIME_TYPE.html,
        **(response_args or dict()),
    )
    return headers_for_cache(r, path=path) if want_cache else headers_for_no_cache(r)


def render_static_jinja(base, ext, j2_ctx, cache_ok=False):
    """Render static template with jinja

    Args:
        base (str): base name of file, e.g. ``user-state``
        ext (str): suffix of file, e.g. ``js``
        j2_ctx (dict): jinja context
        cache_ok (bool): OK to cache the result? [default: False]

    Returns:
        Response: reply
    """
    p = sirepo.resource.static(ext, f"{base}.{ext}")
    r = gen_response(
        pkjinja.render_file(p, j2_ctx, strict_undefined=True),
        content_type=MIME_TYPE[ext],
    )
    if cache_ok:
        return headers_for_cache(r, path=p)
    return headers_for_no_cache(r)


def _as_attachment(resp, content_type, filename):
    resp.mimetype = content_type
    resp.headers["Content-Disposition"] = 'attachment; filename="{}"'.format(filename)
    return resp


def _gen_exception_error(qcall, exc):
    pkdlog("unsupported exception={} msg={}", type(exc), exc)
    if qcall.sreq.is_spider():
        return gen_response(
            """<!doctype html><html>
<head><title>500 Internal Server Error</title></head>
<body><h1>Internal Server Error</h1></body>
</html>
""",
            content_type=MIME_TYPE.html,
            status=500,
        )
    return gen_redirect_for_local_route(qcall, None, route="error")


def _gen_exception_base(qcall, exc):
    return _gen_exception_reply(qcall, exc)


def _gen_exception_reply(qcall, exc):
    f = getattr(
        pykern.pkinspect.this_module(),
        "_gen_exception_reply_" + exc.__class__.__name__,
        None,
    )
    pkdc("exception={} sr_args={}", exc, exc.sr_args)
    if not f:
        return _gen_exception_error(qcall, exc)
    return f(qcall, exc.sr_args)


def _gen_exception_reply(qcall, exc):
    f = getattr(
        pykern.pkinspect.this_module(),
        "_gen_exception_reply_" + exc.__class__.__name__,
        None,
    )
    pkdc("exception={} sr_args={}", exc, exc.sr_args)
    if not f:
        return _gen_exception_error(qcall, exc)
    return f(qcall, exc.sr_args)


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
        return gen_json(args.pkupdate({_STATE: _ERROR_STATE}))
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


def _gen_exception_reply_Response(qcall, args):
    r = args.response
    assert isinstance(
        r, sirepo.flask.app().response_class
    ), "invalid class={} response={}".format(type(r), r)
    return r


def _gen_exception_reply_ServerError(qcall, args):
    return _gen_http_exception(500)


def _gen_exception_reply_SPathNotFound(qcall, args):
    pkdlog("uncaught SPathNotFound {}", args)
    return gen_response(
        """<!doctype html><html>
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
        assert r in s.localRoutes, "route={} not found in schema for type={}".format(
            r, t
        )
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
        PKDict({_STATE: _ERROR_STATE, _ERROR_STATE: args.error}),
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
            pkdlog("customErrors code={} render error={} stack={}", code, e, pkdexc())
    # If there isn't a customError, then render empty reponse
    return headers_for_no_cache(gen_response(status=code))


def _gen_tornado_exception_reply_SRException(args):
    return PKDict({_STATE: SR_EXCEPTION_STATE, SR_EXCEPTION_STATE: args})


def _gen_tornado_exception_reply_UserAlert(args):
    return PKDict({_STATE: _ERROR_STATE, _ERROR_STATE: args.error})
