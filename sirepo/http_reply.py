# -*- coding: utf-8 -*-
u"""response generation

:copyright: Copyright (c) 2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkconfig
from pykern import pkconst
from pykern import pkio
from pykern import pkjson
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp
import flask
import mimetypes
import pykern.pkinspect
import re
import sirepo.http_request
import sirepo.uri
import sirepo.util
import werkzeug.exceptions


#: data.state for srException
SR_EXCEPTION_STATE = 'srException'

#: mapping of extension (json, js, html) to MIME type
MIME_TYPE = None

_ERROR_STATE = 'error'

_STATE = 'state'

#: Default response
_RESPONSE_OK = PKDict({_STATE: 'ok'})

#: Parsing errors from subprocess
_SUBPROCESS_ERROR_RE = re.compile(r'(?:warning|exception|error): ([^\n]+?)(?:;|\n|$)', flags=re.IGNORECASE)

#: routes that will require a reload
_RELOAD_JS_ROUTES = None

def as_attachment(resp, content_type, filename):
    resp.mimetype = content_type
    resp.headers['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
    return resp


def gen_exception(exc):
    """Generate from an Exception

    Args:
        exc (Exception): valid convert into a response
    """
    # If an exception occurs here, we'll fall through
    # to flask, which will have code to handle this case.
    if isinstance(exc, sirepo.util.Reply):
        return _gen_exception_reply(exc)
    if isinstance(exc, werkzeug.exceptions.HTTPException):
        return _gen_exception_werkzeug(exc)
    return _gen_exception_error(exc)


def gen_file_as_attachment(content_or_path, filename=None, content_type=None):
    """Generate a flask file attachment response

    Args:
        content_or_path (bytes or py.path): File contents
        filename (str): Name of file [content_or_path.basename]
        content_type (str): MIMETYPE of file [guessed]

    Returns:
        flask.Response: reply object
    """
    def f():
        if isinstance(content_or_path, pkconst.PY_PATH_LOCAL_TYPE):
            return flask.send_file(str(content_or_path))
        return flask.current_app.response_class(content_or_path)

    if filename is None:
        # dies if content_or_path is not a path
        filename = content_or_path.basename
    if content_type is None:
        content_type, _ = mimetypes.guess_type(filename)
        if content_type is None:
            content_type = 'application/octet-stream'
        # overrule mimetypes for this case
        elif content_type == 'text/x-python':
            content_type = 'text/plain'
    return headers_for_no_cache(
        as_attachment(f(), content_type, filename))


def gen_json(value, pretty=False, response_kwargs=None):
    """Generate JSON flask response

    Args:
        value (dict): what to format
        pretty (bool): pretty print [False]
    Returns:
        flask.Response: reply object
    """
    app = flask.current_app
    if not response_kwargs:
        response_kwargs = PKDict()
    return app.response_class(
        simulation_db.generate_json(value, pretty=pretty),
        mimetype=MIME_TYPE.json,
        **response_kwargs
    )


def gen_json_ok(*args, **kwargs):
    """Generate state=ok JSON flask response

    Returns:
        flask.Response: reply object
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
        flask.Response: reply object
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
        flask.Response: reply object
    """
    return render_static(
        'javascript-redirect',
        'html',
        PKDict(redirect_uri=uri, **kwargs),
    )


def gen_redirect_for_app_root(sim_type):
    """Redirect to app root for sim_type

    Args:
        sim_type (str): valid sim_type or None [http_request.sim_type]
    Returns:
        flask.Response: reply object
    """
    return gen_redirect_for_anchor(sirepo.uri.app_root(sim_type))


def gen_redirect_for_local_route(sim_type=None, route=None, params=None, query=None, **kwargs):
    """Generate a javascript redirect to sim_type/route/params

    Default route (None) only supported for ``default``
    application_mode/appMode.

    Args:
        sim_type (str): how to find the schema [http_request.sim_type]
        route (str): name in localRoutes [None: use default route]
        params (dict): parameters for route (including :Name)

    Returns:
        flask.Response: reply object
    """
    return gen_redirect_for_anchor(
        sirepo.uri.local_route(sim_type, route, params, query),
        **kwargs
    )


def gen_tornado_exception(exc):
    if not isinstance(exc, sirepo.util.Reply):
        raise
    return getattr(
        pykern.pkinspect.this_module(),
        '_gen_tornado_exception_reply_' + exc.__class__.__name__,
    )(exc.sr_args)


def headers_for_no_cache(resp):
    resp.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    resp.headers['Pragma'] = 'no-cache'
    return resp


def init(**imports):
    global MIME_TYPE, _RELOAD_JS_ROUTES

    sirepo.util.setattr_imports(imports)
    MIME_TYPE = PKDict(
        html='text/html',
        js='application/javascript',
        json='application/json',
        py='text/x-python',
        madx='text/plain',
    )
    s = simulation_db.get_schema(sim_type=None)
    _RELOAD_JS_ROUTES = frozenset(
        (k for k, v in s.localRoutes.items() if v.get('requireReload')),
    )


def render_static(base, ext, j2_ctx, cache_ok=False):
    """Call flask.render_template appropriately

    Args:
        base (str): base name of file, e.g. ``user-state``
        ext (str): suffix of file, e.g. ``js``
        j2_ctx (dict): jinja context
        cache_ok (bool): OK to cache the result? [default: False]

    Returns:
        object: Flask.Response
    """
    fn = '{}/{}.{}'.format(ext, base, ext)
    r = flask.Response(
        flask.render_template(fn, **j2_ctx),
        mimetype=MIME_TYPE[ext],
    )
    if not cache_ok:
        r = headers_for_no_cache(r)
    return r


def _gen_exception_error(exc):
    pkdlog('unsupported exception={} msg={}', type(exc), exc)
    return gen_redirect_for_local_route(None, route='error')


def _gen_exception_reply(exc):
    f = getattr(
        pykern.pkinspect.this_module(),
        '_gen_exception_reply_' + exc.__class__.__name__,
        None,
    )
    pkdc('exception={} sr_args={}', exc, exc.sr_args)
    if not f:
        return _gen_exception_error(exc)
    return f(exc.sr_args)


def _gen_exception_reply_Error(args):
    try:
        t = sirepo.http_request.sim_type(args.pkdel('sim_type'))
        s = simulation_db.get_schema(sim_type=t)
    except Exception:
        # sim_type is bad so don't cascade errors, just
        # try to get the schema without the type
        t = None
        s = simulation_db.get_schema(sim_type=None)
    if flask.request.method == 'POST':
        return gen_json(args.pkupdate({_STATE: _ERROR_STATE}))
    q = PKDict()
    for k, v in args.items():
        try:
            v = str(v)
            assert len(v) < 200, 'value is too long (>=200 chars)'
        except Exception as e:
            pkdlog('error in "error" query {}={} exception={}', k, v, e)
            continue
        q[k] = v
    return gen_redirect_for_local_route(t, route='error', query=q)


def _gen_exception_reply_Redirect(args):
    return gen_redirect(args.uri)


def _gen_exception_reply_Response(args):
    r = args.response
    assert isinstance(r, flask.current_app.response_class), \
        'invalid class={} response={}'.format(type(r), r)
    return r


def _gen_exception_reply_SRException(args):
    r = args.routeName
    p = args.params or PKDict()
    try:
        t = sirepo.http_request.sim_type(p.pkdel('sim_type'))
        s = simulation_db.get_schema(sim_type=t)
    except Exception as e:
        pkdc('exception={} stack={}', e, pkdexc())
        # sim_type is bad so don't cascade errors, just
        # try to get the schema without the type
        t = None
        s = simulation_db.get_schema(sim_type=None)
    # If default route or always redirect/reload
    if r:
        assert r in s.localRoutes, \
            'route={} not found in schema for type={}'.format(r, t)
    else:
        r = sirepo.uri.default_local_route_name(s)
        p = PKDict(reload_js=True)
    if (
        # must be first, to always delete reload_js
        not p.pkdel('reload_js')
        and flask.request.method == 'POST'
        and r not in _RELOAD_JS_ROUTES
    ):
        pkdc('POST response={} route={} params={}', SR_EXCEPTION_STATE, r, p)
        return gen_json(
            PKDict({
                _STATE: SR_EXCEPTION_STATE,
                SR_EXCEPTION_STATE: args,
            }),
        )
    pkdc('redirect to route={} params={}  type={}', r, p, t)
    return gen_redirect_for_local_route(
        t,
        route=r,
        params=p,
        sr_exception=pkjson.dump_pretty(args, pretty=False),
    )


def _gen_exception_reply_UserAlert(args):
    return gen_json(
        PKDict({_STATE: _ERROR_STATE, _ERROR_STATE: args.error}),
    )


def _gen_exception_werkzeug(exc):
#TODO(robnagler) convert exceptions to our own
    raise exc


def _gen_tornado_exception_reply_SRException(args):
    return PKDict({_STATE: SR_EXCEPTION_STATE, SR_EXCEPTION_STATE: args})


def _gen_tornado_exception_reply_UserAlert(args):
    return PKDict({_STATE: _ERROR_STATE, _ERROR_STATE: args.error})
