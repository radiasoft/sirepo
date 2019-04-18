# -*- coding: utf-8 -*-
u"""basic auth implementation

:copyright: Copyright (c) 2019 Bivio Software, Inc.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkconfig
import flask

#: bots only
AUTH_METHOD_VISIBLE = False

def require_user():
    """Check for basic auth credentials against db
    """
    a = flask.request.authenticate
    if a and a.type == 'basic':
        if _check(a.username, a.password):
            return None
    return flask.current_app.response_class(
        status=401,
        headers={'WWW-Authenticate': 'Basic realm="*"'},
    )


def _cfg_uid(value):
    assert simulation_db.user_dir_name(cfg.uid).exists(dir=True), \
        'uid={} does not exist'.format(cfg.uid)
    return value


def _check(username, password):
    return cfg.uid == username and cfg.password == password


def init_apis(**args, **kwargs):
    pass
