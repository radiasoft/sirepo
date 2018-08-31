# -*- coding: utf-8 -*-
u"""User state management via an HTTP cookie

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function

from pykern import pkcollections
from pykern import pkconfig
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp
from sirepo import util
import base64
import flask
import re
import cryptography.fernet

_MAX_AGE_SECONDS = 10 * 365 * 24 * 3600

#: Identifies if the cookie has been returned by the client
_COOKIE_SENTINEL = 'srk'

#: Identifies the user in the cookie
_COOKIE_USER = 'sru'

_SERIALIZER_SEP = ' '

def clear_user():
    unchecked_remove(_COOKIE_USER)


def get_value(key):
    return _state()[key]


def get_user(checked=True):
    return _state().get_user(checked)


def has_key(key):
    return key in _state()


def init():
    header = flask.request.environ.get('HTTP_COOKIE', '')
    assert not 'sirepo_cookie' in flask.g
    flask.g.sirepo_cookie = _State(header)


def init_mock(uid):
    """A mock cookie for pkcli"""
    flask.g = pkcollections.Dict({
        'sirepo_cookie': _State('', None),
    })
    set_value(_COOKIE_SENTINEL, 1)
    set_user(uid)


def save_to_cookie(response):
    _state().save_to_cookie(response)


def set_value(key, value):
    assert not _SERIALIZER_SEP in value, 'value must not container serializer sep "{}"'.format(_SERIALIZER_SEP)
    _state()[key] = value


def set_user(uid):
    assert uid
    set_value(_COOKIE_USER, uid)


def unchecked_remove(key):
    if key in _state():
        del _state()[key]


def _state():
    return flask.g.sirepo_cookie


class _State(dict):

    def __init__(self, header):
        self.incoming_cookie_text = ''
        self.crypto = None
        self._from_cookie_header(header)

    def get_user(self, checked=True):
        if not self.get(_COOKIE_SENTINEL):
            util.raise_forbidden('Missing sentinel, cookies may be disabled')
        return self[_COOKIE_USER] if checked else self.get(_COOKIE_USER)

    def save_to_cookie(self, response):
        if 200 <= response.status_code < 400:
            self[_COOKIE_SENTINEL] = 1
            text = ' '.join(map(lambda k: '{}={}'.format(k, self[k]), self.keys()))
            if text != self.incoming_cookie_text:
                response.set_cookie(cfg.key, self._encode_value(text), max_age=_MAX_AGE_SECONDS)

    def _crypto(self):
        if not self.crypto:
            if pkconfig.channel_in('dev') and not cfg.secret:
                cfg.secret = 'dev dummy secret'
            assert cfg.secret
            key = bytes(cfg.secret)
            # pad key to required 32 bytes
            self.crypto = cryptography.fernet.Fernet(base64.urlsafe_b64encode(key + '\0' * (32 - len(key))))
        return self.crypto


    def _decode_value(self, value):
        try:
            return self._crypto().decrypt(base64.urlsafe_b64decode(value))
        except cryptography.fernet.InvalidToken:
            pkdlog('Cookie decryption failed: {}', value)
            return ''

    def _encode_value(self, text):
        return base64.urlsafe_b64encode(self._crypto().encrypt(text))

    def _from_cookie_header(self, header):
        match = re.search(r'\b{}=([^;]+)'.format(cfg.key), header)
        if match:
            try:
                values = self._decode_value(match.group(1))
            except TypeError:
                values = ''
            self.incoming_cookie_text = values
            for pair in values.split(' '):
                match = re.search(r'^([^=]+)=(.*)', pair)
                if match:
                    k, v = match.groups(1)
                    self[k] = v
        if not self.get(_COOKIE_SENTINEL):
            import sirepo.beaker_compat
            sirepo.beaker_compat.update_session_from_cookie_header(header)


cfg = pkconfig.init(
    key=('sirepo_' + pkconfig.cfg.channel, str, 'Name of the cookie key used to save the session under'),
    secret=(None, str, 'Cookie encryption secret'),
)
