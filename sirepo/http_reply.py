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
    """Generate from a `util.Reply` exception

    Args:
        exc (util.Reply): valid reply exceptoin
    """

    assert isinstance(exc, sirepo.util.Reply), \
        'exc={} not a sirepo.util.Reply'.format(exc)
    if isinstance(exc, sirepo.util.SRException):
        s = simulation_db.get_schema(sim_type=None)
        assert exc.sr_args.routeName in s.localRoutes, \
            'route={} not found in schema={}'.format(
                exc.sr_args.routeName,
                s.simulationType,
            )
        return gen_json(
            PKDict({
                _STATE: SR_EXCEPTION_STATE,
                SR_EXCEPTION_STATE: exc.sr_args,
            }),
            response_kwargs=pkcollections.Dict(status=SR_EXCEPTION_STATUS),
        )
    elif isinstance(exc, sirepo.util.UserAlert):
        return gen_json(PKDict({
            _STATE: _ERROR_STATE,
            _ERROR_STATE: exc.sr_args.error,
        }))
    elif isinstance(exc, sirepo.util.Redirect):
        return gen_redirect(exc.sr_args.uri)
    else:
        raise AssertionError('unsupported exception={}'.format(type(exc)))


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
        sim_type (str): valid sim_type or None
    Returns:
        flask.Response: reply object
    """
    import sirepo.uri

    return gen_redirect_for_anchor(sirepo.uri.app_root(sim_type))


def gen_redirect_for_local_route(sim_type, route=None, params=None, query=None):
    """Generate a javascript redirect to sim_type/route/params

    Default route (None) only supported for ``default``
    application_mode/appMode.

    Args:
        sim_type (str): how to find the schema
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


def subprocess_error(err, *args, **kwargs):
    """Something unexpected went wrong.

    Parses ``err`` for error

    Args:
        err (str): exception or run_log
        quiet (bool): don't write errors to log
    Returns:
        dict: error response
    """
    if not kwargs.get('quiet'):
        pkdlog('{}', ': '.join([str(a) for a in args] + ['error', err]))
    m = re.search(_SUBPROCESS_ERROR_RE, str(err))
    if m:
        err = m.group(1)
        if re.search(r'error exit\(-15\)', err):
            err = 'Terminated'
    elif not pkconfig.channel_in_internal_test():
        err = 'unexpected error (see logs)'
    return {'state': 'error', 'error': err}
