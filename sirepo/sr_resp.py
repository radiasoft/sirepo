# -*- coding: utf-8 -*-
u"""response generation

:copyright: Copyright (c) 2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp
from sirepo import simulation_db
from sirepo import util
import flask


#: _json_response_ok cache
_JSON_RESPONSE_OK = None

# Default response
_RESPONSE_OK = {'state': 'ok'}

#: Mimetype (cache) used for json replies
_JSON_MIMETYPE = None


def gen_json(value, pretty=False):
    """Generate JSON flask response

    Args:
        value (dict): what to format
        pretty (bool): pretty print [False]
    Returns:
        Response: flask response
    """
    global _JSON_MIMETYPE

    app = flask.current_app
    if not _JSON_MIMETYPE:
        _JSON_MIMETYPE = app.config.get('JSONIFY_MIMETYPE', 'application/json')
    return app.response_class(
        simulation_db.generate_json(value, pretty=pretty),
        mimetype=_JSON_MIMETYPE,
    )


def gen_json_ok(*args, **kwargs):
    """Generate state=ok JSON flask response

    Returns:
        Response: flask response
    """
    if len(args) > 0:
        assert len(args) == 1
        res = args[0]
        res.update(_RESPONSE_OK)
        return gen_json(res)

    global _JSON_RESPONSE_OK
    if not _JSON_RESPONSE_OK:
        _JSON_RESPONSE_OK = gen_json(_RESPONSE_OK)
    return _JSON_RESPONSE_OK
