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
import cryptography.fernet
import flask
import itertools
import re


_MAX_AGE_SECONDS = 10 * 365 * 24 * 3600

#: Identifies if the cookie has been returned by the client
_COOKIE_SENTINEL = 'srk'

#: Unique, truthy that can be asserted on decrypt
_COOKIE_SENTINEL_VALUE = 'z'

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


def init(unit_test=None):
    if not unit_test:
        assert not 'sirepo_cookie' in flask.g
    _State(unit_test or flask.request.environ.get('HTTP_COOKIE', ''))


def init_mock(uid='invalid-uid'):
    """A mock cookie for pkcli"""
    flask.g = pkcollections.Dict()
    _State('')
    prepare_for_fresh_login()
    set_user(uid)


def prepare_for_fresh_login():
    """Called in special authentication cases

    Bypasses the state where the cookie has not come back from the
    client. This is used by bluesky and testing only, right now.
    """
    _state().set_sentinel()


def save_to_cookie(response):
    _state().save_to_cookie(response)


def set_value(key, value):
    value = str(value)
    assert not _SERIALIZER_SEP in value, \
        'value must not container serializer sep "{}"'.format(_SERIALIZER_SEP)
    s = _state()
    assert key == _COOKIE_SENTINEL or _COOKIE_SENTINEL in s, \
        'cookie is not valid so cannot set key={}'.format(key)
    s[key] = value


def set_user(uid):
    assert uid
    set_value(_COOKIE_USER, uid)


def unchecked_remove(key):
    try:
        del _state()[key]
    except KeyError:
       pass


class _State(dict):

    def __init__(self, header):
        self.incoming_serialized = ''
        self.crypto = None
        flask.g.sirepo_cookie = self
        self._from_cookie_header(header)

    def get_user(self, checked=True):
        if not self.get(_COOKIE_SENTINEL):
            util.raise_forbidden('Missing sentinel, cookies may be disabled')
        return self[_COOKIE_USER] if checked else self.get(_COOKIE_USER)

    def set_sentinel(self):
        self[_COOKIE_SENTINEL] = _COOKIE_SENTINEL_VALUE

    def save_to_cookie(self, response):
        if not 200 <= response.status_code < 400:
            return
        self.set_sentinel()
        s = self._serialize()
        if s == self.incoming_serialized:
            return
        response.set_cookie(
            cfg.http_name,
            self._encrypt(s),
            max_age=_MAX_AGE_SECONDS,
            httponly=True,
            secure=cfg.is_secure,
        )

    def _crypto(self):
        if not self.crypto:
            self.crypto = cryptography.fernet.Fernet(cfg.private_key)
        return self.crypto


    def _decrypt(self, value):
        return self._crypto().decrypt(base64.urlsafe_b64decode(value))

    def _deserialize(self, value):
        v = value.split(_SERIALIZER_SEP)
        v = dict(zip(v[::2], v[1::2]))
        assert v[_COOKIE_SENTINEL] == _COOKIE_SENTINEL_VALUE, \
            'cookie sentinel value is not correct'
        return v

    def _encrypt(self, text):
        return base64.urlsafe_b64encode(self._crypto().encrypt(text))

    def _from_cookie_header(self, header):
        s = None
        err = None
        try:
            match = re.search(r'\b{}=([^;]+)'.format(cfg.http_name), header)
            if match:
                s = self._decrypt(match.group(1))
                self.update(self._deserialize(s))
                self.incoming_serialized = s
                return
        except Exception as e:
            if 'crypto' in type(e).__module__:
                # cryptography module exceptions serialize to empty string
                # so just report the type.
                e = type(e)
            err = e
            pkdc(pkdexc())
            # wait for decoding errors until after beaker attempt
        if not self.get(_COOKIE_SENTINEL):
            import sirepo.beaker_compat
            res = sirepo.beaker_compat.update_session_from_cookie_header(header)
            if not res is None:
                self.clear()
                self.update(res)
                self.set_sentinel()
                err = None
        if err:
            pkdlog('Cookie decoding failed: {} value={}', err, s)

    def _serialize(self):
        return _SERIALIZER_SEP.join(
            itertools.chain.from_iterable(
                [(k, self[k]) for k in sorted(self.keys())],
            ),
        )


@pkconfig.parse_none
def _cfg_private_key(value):
    if value is None:
        assert pkconfig.channel_in('dev'), \
            'must configure private_key in non-dev channel={}'.format(pkconfig.cfg.channel)
        value = base64.urlsafe_b64encode(b'01234567890123456789012345678912')
    assert len(base64.urlsafe_b64decode(value)) == 32, \
        'must be 32 characters and encoded with urlsafe_b64encode'
    return value


@pkconfig.parse_none
def _cfg_http_name(value):
    assert re.search(r'^\w{1,32}$', value), \
        'must be 1-32 word characters; http_name={}'.format(value)
    return value


def _state():
    return flask.g.sirepo_cookie


cfg = pkconfig.init(
    http_name=('sirepo_' + pkconfig.cfg.channel, _cfg_http_name, 'Set-Cookie name'),
    private_key=(None, _cfg_private_key, 'urlsafe base64 encrypted 32-byte key'),
    is_secure=(
        not pkconfig.channel_in('dev'),
        pkconfig.parse_bool,
        'Add secure attriute to Set-Cookie',
    )
)
