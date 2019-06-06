# -*- coding: utf-8 -*-
u"""response generation

:copyright: Copyright (c) 2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp
from pykern import pkcollections
from sirepo import util
import flask
import re

#: HTTP status code for srException (BAD REQUEST)
SR_EXCEPTION_STATUS = 400

#: data.state for srException
SR_EXCEPTION_STATE = 'srException'

#: mapping of extension (json, js, html) to MIME type
MIME_TYPE = None

STATE = 'state'

#: Default response
_RESPONSE_OK = pkcollections.Dict({STATE: 'ok'})


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


def gen_redirect_for_anchor(uri):
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


def gen_redirect_for_local_route(sim_type, route=None, params=None):
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
    s = simulation_db.get_schema(sim_type)
    if not route:
        route = s.appModes.default.localRoute
    parts = s.localRoutes[route].route.split('/:')
    u = parts.pop(0)
    for p in parts:
        if p.endswith('?'):
            p = p[:-1]
            if not params or p not in params:
                continue
        u += '/' + params[p]
    return gen_redirect_for_anchor('/{}#{}'.format(sim_type, u))


def gen_redirect_for_root(sim_type, **kwargs):
    """Redirect to app root for sim_type

    Args:
        sim_type (str): valid sim_type or None
    Returns:
        flask.Response: reply object
    """
    if not sim_type:
        sim_type = ''
    return flask.redirect('/' + sim_type, **kwargs)


def gen_sr_exception(route, params=None):
    """Generate json response for srException

    Args:
        route (str): name (not uri) in localRoutes
        params (dict): params for route [None]

    Returns:
        flask.Response: reply object
    """
    s = simulation_db.get_schema(sim_type=None)
    assert route in s.localRoutes, \
        'route={} not found in schema='.format(route, s.simulationType)
    pkdlog('srException: route={} params={}', route, params)
    return gen_json(
        pkcollections.Dict({
            STATE: SR_EXCEPTION_STATE,
            SR_EXCEPTION_STATE: pkcollections.Dict(
                routeName=route,
                params=params,
            ),
        }),
        response_kwargs=pkcollections.Dict(status=SR_EXCEPTION_STATUS),
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
