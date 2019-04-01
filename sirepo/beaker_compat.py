# -*- coding: utf-8 -*-
u"""Backward compatibility for old Beaker sessions.

:copyright: Copyright (c) 2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html

"""
from __future__ import absolute_import, division, print_function

from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp
from pykern import pkconfig
import beaker.session
import flask
import pickle


_ORIG_KEY = 'uid'

oauth_hook = None


def update_session_from_cookie_header(header):
    """Update the flask session from the beaker file identified by the cookie header
    """
    maps = _init_maps()
    try:
        cookie = beaker.session.SignedCookie(cfg.secret, input=header)
        if not cfg.key in cookie:
            return None
        identifier = cookie[cfg.key].value
        if not identifier:
            return None
        path = beaker.util.encoded_path(
            str(flask.current_app.sirepo_db_dir.join('beaker/container_file')),
            [identifier],
            extension='.cache',
            digest_filenames=False,
        )
        with open(path, 'rb') as fh:
            values = pickle.load(fh)
        res = {}
        if 'session' in values and _ORIG_KEY in values['session']:
            for f in maps['key'].keys():
                v = values['session'].get(f)
                if not v is None:
                    if not isinstance(v, str):
                        # pickle decodes certains strings as unicode in Python 2
                        v = v.encode('ascii')
                    res[maps['key'][f]] = maps['value'].get(v, v)
            pkdlog('retrieved user from beaker cookie: res={}', res)
        return res
    except Exception as e:
        pkdlog('ignoring exception with beaker compat: error={}, header={}', e, header)
    return None


@pkconfig.parse_none
def _cfg_session_secret(value):
    """Reads file specified as config value"""
    if not value:
        assert pkconfig.channel_in('dev'), 'missing session secret configuration'
        return 'dev dummy secret'
    with open(value) as f:
        return f.read()


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


cfg = pkconfig.init(
    key=('sirepo_' + pkconfig.cfg.channel, str, 'Beaker: Name of the cookie key used to save the session under'),
    secret=(None, _cfg_session_secret, 'Beaker: Used with the HMAC to ensure session integrity'),
)
