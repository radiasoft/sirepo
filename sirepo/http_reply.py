# -*- coding: utf-8 -*-
u"""response generation

:copyright: Copyright (c) 2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp
from pykern import pkcollections
from sirepo import simulation_db
from sirepo import util
import flask

#: HTTP status code for srException
SR_EXCEPTION_STATUS = 400

#: data.state for srException
SR_EXCEPTION_STATE = 'srException'

#: mapping of extension (json, js, html) to MIME type
MIME_TYPE = None

STATE = 'state'

#: Default response
_RESPONSE_OK = {STATE: 'ok'}


def gen_json(value, pretty=False, response_kwargs=None):
    """Generate JSON flask response

    Args:
        value (dict): what to format
        pretty (bool): pretty print [False]
    Returns:
        Response: flask response
    """
    app = flask.current_app
    if not response_kwargs:
        response_kwargs = {}
    return app.response_class(
        simulation_db.generate_json(value, pretty=pretty),
        mimetype=MIME_TYPE.json,
        **response_kwargs
    )


def gen_json_ok(*args, **kwargs):
    """Generate state=ok JSON flask response

    Returns:
        Response: flask response
    """
    if not args:
        # do not cache this, see #1390
        return gen_json(_RESPONSE_OK)
    assert len(args) == 1
    res = args[0]
    res.update(_RESPONSE_OK)
    return gen_json(res)


def gen_sr_exception(route_name):
    """Generate json response for srException

    Args:
        route_name (str): name (not uri) in localRoutes

    Returns:
        object: Flask response
    """
    #TODO(robnagler) assert route, but don't have sim_type
    return gen_json(
        {
            STATE: SR_EXCEPTION_STATE,
            SR_EXCEPTION_STATE: {'routeName': route_name},
        },
        response_kwargs=dict(status=SR_EXCEPTION_STATUS),
    )


def headers_for_no_cache(resp):
    resp.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    resp.headers['Pragma'] = 'no-cache'
    return resp


def init_by_server(app):
    global MIME_TYPE
    if MIME_TYPE:
        return
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
