# -*- coding: utf-8 -*-
u"""HTTP Basic Auth Login

:copyright: Copyright (c) 2019 Bivio Software, Inc.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkconfig
import flask


AUTH_METHOD = 'basic'

#: bots only
AUTH_METHOD_VISIBLE = False


def require_user():
    """Check for basic auth credentials against cfg
    """
    v = flask.request.authorization
    if v and v.type == 'basic' and _check(v):
        return cfg.uid
    return None


def _cfg_uid(value):
    from sirepo import simulation_db

    assert simulation_db.user_dir_name(value).check(dir=True), \
        'uid={} does not exist'.format(value)
    return value


def _check(v):
    return cfg.uid == v.username and cfg.password == v.password


def init_apis(*args, **kwargs):
    global cfg
    cfg = pkconfig.init(
        uid=pkconfig.Required(_cfg_uid, 'single user allowed to login with basic auth'),
        password=pkconfig.Required(str, 'password for uid'),
    )
