# -*- coding: utf-8 -*-
u"""Backward compatibility for old Beaker sessions.

:copyright: Copyright (c) 2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html

"""
from __future__ import absolute_import, division, print_function

from beaker.session import SignedCookie
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp
import beaker
import flask
import pickle


def update_session_from_cookie_header(header):
    """Update the flask session from the beaker file identified by the cookie header
    """
    from sirepo.server import cfg
    try:
        cookie = SignedCookie(cfg.beaker_session.secret, input=header)
        if cfg.beaker_session.key in cookie:
            identifier = cookie[cfg.beaker_session.key].value
            if not identifier:
                return
            path = beaker.util.encoded_path(
                str(cfg.db_dir.join('beaker/container_file')),
                [identifier],
                extension='.cache',
                digest_filenames=False)
            with open(path, 'rb') as fh:
                values = pickle.load(fh)
                if 'session' in values and 'uid' in values['session']:
                    pkdlog('retrieved user from beaker cookie: {}', values['session']['uid'])
                    for f in ('uid', 'oauth_login_state', 'oauth_user_name'):
                        if f in values['session']:
                            flask.session[f] = values['session'][f]
    except Exception as e:
        pkdlog('ignoring exception with beaker compat: e: {}, header: {}', e, header)
    return
