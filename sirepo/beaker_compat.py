# -*- coding: utf-8 -*-
u"""Backward compatibility for old Beaker sessions.

:copyright: Copyright (c) 2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html

"""
from __future__ import absolute_import, division, print_function

from beaker.session import SignedCookie
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp
import beaker
import pickle


_ORIG_KEY = 'uid'

oauth_hook = None


def update_session_from_cookie_header(header):
    """Update the flask session from the beaker file identified by the cookie header
    """
    from sirepo.server import cfg

    maps = _init_maps()
    try:
        cookie = SignedCookie(cfg.beaker_session.secret, input=header)
        if not cfg.beaker_session.key in cookie:
            return None
        identifier = cookie[cfg.beaker_session.key].value
        if not identifier:
            return None
        path = beaker.util.encoded_path(
            str(cfg.db_dir.join('beaker/container_file')),
            [identifier],
            extension='.cache',
            digest_filenames=False)
        with open(path, 'rb') as fh:
            values = pickle.load(fh)
        res = {}
        if 'session' in values and _ORIG_KEY in values['session']:
            # beaker session was found but empty or no uid so
            for f in maps['key'].keys():
                if f in values['session']:
                    res[maps['key'][f]] = maps['value'].get(
                        values['session'][f], values['session'][f],
                    )
            pkdlog('retrieved user from beaker cookie: res={}', res)
        return res
    except Exception as e:
        pkdlog('ignoring exception with beaker compat: error={}, header={}', e, header)
    return None


def _init_maps():
    import sirepo.cookie

    res = {
        'key': {
            _ORIG_KEY: sirepo.cookie._COOKIE_USER,
        },
        'value': {}
    }
    if oauth_hook:
        oauth_hook(res)
    return res
