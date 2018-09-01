# -*- coding: utf-8 -*-
u"""Backward compatibility for old Beaker sessions.

:copyright: Copyright (c) 2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html

"""
from __future__ import absolute_import, division, print_function

from beaker.session import SignedCookie
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp
from sirepo import cookie
import beaker
import pickle
import sirepo

_ORIG_KEY = 'uid'

def update_session_from_cookie_header(header):
    """Update the flask session from the beaker file identified by the cookie header
    """
    from sirepo.server import cfg
    maps = _init_maps(cfg.oauth_login)
    try:
        cookie = SignedCookie(cfg.beaker_session.secret, input=header)
        if cfg.beaker_session.key in cookie:
            identifier = cookie[cfg.beaker_session.key].value
            if not identifier:
                return False
            path = beaker.util.encoded_path(
                str(cfg.db_dir.join('beaker/container_file')),
                [identifier],
                extension='.cache',
                digest_filenames=False)
            with open(path, 'rb') as fh:
                values = pickle.load(fh)
            if 'session' in values and _ORIG_KEY in values['session']:
                pkdlog('retrieved user from beaker cookie: {}', values['session'][_ORIG_KEY])
                for f in maps['key'].keys():
                    if f in values['session']:
                        sirepo.cookie.set_value(
                            maps['key'][f],
                            maps['value'].get(values['session'][f], values['session'][f]),
                        )
            else:
                # beaker session was found but empty or no uid so
                sirepo.cookie.clear_user()
            return True
    except Exception as e:
        pkdlog('ignoring exception with beaker compat: e: {}, header: {}', e, header)
    return False


def _init_maps(is_oauth):
    res = {
        'key': {
            _ORIG_KEY: cookie._COOKIE_USER,
        },
        'value': {}
    }
    if is_oauth:
        from sirepo import oauth
        res['key']['oauth_login_state'] = oauth._COOKIE_STATE
        res['key']['oauth_user_name'] = oauth._COOKIE_NAME
        # reverse map of login state values
        res['value'] = dict(map(lambda k: (oauth._LOGIN_STATE_MAP[k], k), oauth._LOGIN_STATE_MAP))
    return res
