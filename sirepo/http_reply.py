# -*- coding: utf-8 -*-
u"""response generation

:copyright: Copyright (c) 2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkcollections
from pykern import pkconfig
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp
import flask
import re
import sirepo.http_request
import sirepo.util


#: HTTP status code for srException (BAD REQUEST)
SR_EXCEPTION_STATUS = 400

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
        return _gen_exception_werzeug(exc)
    return _gen_exception_error(exc)


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
        response_kwargs = pkcollections.Dict()
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
    return gen_redirect_for_anchor(uri=uri)


def gen_redirect_for_anchor(uri, **kwargs):
    """Redirect uri with an anchor using javascript

    Safari browser doesn't support redirects with anchors so we do this
    in all cases.

    Args:
        uri (str): where to redirect to
    Returns:
        flask.Response: reply object
    """
    return render_static(
        'javascript-redirect',
        'html',
        pkcollections.Dict(redirect_uri=uri),
    )


def gen_redirect_for_app_root(sim_type):
    """Redirect to app root for sim_type

    Args:
        sim_type (str): valid sim_type or None [http_request.sim_type]
    Returns:
        flask.Response: reply object
    """
    import sirepo.uri

    return gen_redirect_for_anchor(sirepo.uri.app_root(sim_type))


def gen_redirect_for_local_route(sim_type=None, route=None, params=None, query=None):
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
    import sirepo.uri

    return gen_redirect_for_anchor(
        sirepo.uri.local_route(sim_type, route, params, query),
    )


def headers_for_no_cache(resp):
    resp.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    resp.headers['Pragma'] = 'no-cache'
    return resp


def init_by_server(app):
    global MIME_TYPE, simulation_db
    if MIME_TYPE:
        return
    from sirepo import simulation_db
    MIME_TYPE = pkcollections.Dict(
        html='text/html',
        js='application/javascript',
        json=app.config.get('JSONIFY_MIMETYPE', 'application/json'),
        py='text/x-python',
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
    return _gen_exception_reply_Error(
        sirepo.util.Error(
            PKDict({_ERROR_STATE: _SERVER_ERROR}),
            'unsupported exception={} stack={}',
            exc,
            pkdexc(),
        ),
    )

def _gen_exception_reply(exc):
    a = exc.sr_args
    f = getattr(
        pkinspect.this_module(),
        '_gen_exception_reply_' + exc.__class__.__name__,
        None,
    )
    if not f:
        return _gen_exception_error(exc)
    return f(a)


def _gen_exception_reply_Error(args):
    if flask.request.method == 'POST':
        return gen_json(args.values.pkupdate(_STATE, _ERROR_STATE))
    return gen_redirect_for_local_route(
        'error',
        PKDict({_ERROR_STATE: a.get(_ERROR_STATE)}),
    )

def _gen_exception_reply_Redirect(args):
    return gen_redirect(args.get('uri'))

def _gen_exception_reply_UserAlert(args):
        return gen_json(
            PKDict({_STATE: _ERROR_STATE, _ERROR_STATE: a.error}),
        )
    else:
        raise AssertionError(

def _gen_exception_reply_SRException(args):
    import sirepo.uri

    try:
        t = sirepo.http_request.sim_type(args.pkdel('sim_type'))
        s = simulation_db.get_schema(sim_type=t)
    except Exception:
        # sim_type is bad so don't cascade errors, just
        # try to get the schema without the type
        t = None
        s = simulation_db.get_schema(sim_type=None)
    # If default route or always redirect/reload
    if not (args.routeName or args.routeName in s.localRoutes):
        if args.routeName:
            pkdlog('route={} not found in schema for type={}', args.routeName, t)
        args.routeName = sirepo.uri.default_local_route_name(s)
    elif flask.request.method == 'POST' and args.routeName != 'error':
        return gen_json(
            PKDict({
                _STATE: SR_EXCEPTION_STATE,
                SR_EXCEPTION_STATE: args,
            }),
            response_kwargs=pkcollections.Dict(status=SR_EXCEPTION_STATUS),
        )
    args.pksetdefault(query=PKDict).query.pkupdate(reload_js=1)
    return gen_redirect_for_local_route(t, route=args.routeName, params=args.params, query=args.query)
