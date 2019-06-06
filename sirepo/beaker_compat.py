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

def from_cookie_header(header):
    """Update the flask session from the beaker file identified by the cookie header
    """
    err = None
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
        if 'session' in values and _ORIG_KEY in values['session']:
            res = {_ascii(k): _ascii(v) for k, v in values['session'].items()}
            pkdlog('retrieved beaker cookie: res={}', res)
            return res
    except Exception as e:
        err = e
    pkdlog('invalid beaker compat: header={} error={}', header, err)
    return None


@pkconfig.parse_none
def _cfg_secret(value):
    """Reads file specified as config value"""
    if not value:
        assert pkconfig.channel_in('dev'), \
            'missing session secret configuration'
        return 'dev dummy secret'
    with open(value) as f:
        return f.read()


def _ascii(v):
    """pickle decodes certains strings as unicode in Python 2"""
    if v is None or isinstance(v, (str)) or not hasattr(v, 'encode'):
        return v
    return v.encode('ascii')


cfg = pkconfig.init(
    key=('sirepo_' + pkconfig.cfg.channel, str, 'Beaker: Name of the cookie key used to save the session under'),
    secret=(None, _cfg_secret, 'Beaker: Used with the HMAC to ensure session integrity'),
)
