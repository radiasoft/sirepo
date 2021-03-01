# -*- coding: utf-8 -*-
u"""User state management via an HTTP cookie

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkcompat
from pykern import pkconfig
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp
import base64
import contextlib
import cryptography.fernet
import flask
import itertools
import re
import sirepo.srcontext
import sirepo.util

#: sirepo.auth gets to override parsing
auth_hook_from_header = None

_MAX_AGE_SECONDS = 10 * 365 * 24 * 3600

#: Identifies if the cookie has been returned at least once by the client
_COOKIE_SENTINEL = 'srk'

#: Unique, truthy that can be asserted on decrypt
_COOKIE_SENTINEL_VALUE = 'z'

_SERIALIZER_SEP = ' '

_SRCONTEXT_KEY = __name__


def get_value(key):
    return _state()[key]


def has_key(key):
    return key in _state()


def has_sentinel():
    return _COOKIE_SENTINEL in _state()


@contextlib.contextmanager
def process_header(unit_test=None):
    with _set_cookie(unit_test or flask.request.environ.get('HTTP_COOKIE', '')):
        yield


def reset_state(error):
    """Clear all values and log `error` with values.

    Args:
        error (str): to be logged
    """
    pkdlog('resetting cookie: error={} values={}', error, _state())
    _state().clear()


def save_to_cookie(resp):
    _state().save_to_cookie(resp)


@contextlib.contextmanager
def set_cookie_outside_of_flask_request(cookie_header=''):
    """A mock cookie for utilities"""
    assert not sirepo.util.in_flask_request(), \
        'Only call from outside a flask request context'
    if cookie_header:
        cookie_header = f'{cfg.http_name}={cookie_header}'
    with _set_cookie(cookie_header):
        set_sentinel()
        yield

def set_sentinel(values=None):
    """Bypasses the state where the cookie has not come back from the client.

    For auth methods that are used outside the GUI (bluesky and basic) and
    testing.

    Args:
        values (dict): set sentinel in this if supplied [None]
    """
    _state().set_sentinel(values)


def set_value(key, value):
    value = str(value)
    assert not _SERIALIZER_SEP in value, \
        'value must not container serializer sep "{}"'.format(_SERIALIZER_SEP)
    s = _state()
    assert key == _COOKIE_SENTINEL or _COOKIE_SENTINEL in s, \
        'cookie is not valid so cannot set key={}'.format(key)
    s[key] = value


def unchecked_get_value(key, default=None):
    return _state().get(key, default)


def unchecked_remove(key):
    try:
        s = _state()
        res = s[key]
        del s[key]
        return res
    except KeyError:
        return None


@contextlib.contextmanager
def _set_cookie(header):
    # Maintain cookie states on stack to allow setting of cookies
    # within a state where a cookie is already set
    p = _state()
    try:
        sirepo.srcontext.set(_SRCONTEXT_KEY, _State(header))
        yield
    finally:
        sirepo.srcontext.set(_SRCONTEXT_KEY, p)


class _State(dict):

    def __init__(self, header):
        super(_State, self).__init__()
        self.crypto = None
        self.incoming_serialized = ''
        self._from_cookie_header(header)

    def set_sentinel(self, values=None):
        if not values:
            values = self
        values[_COOKIE_SENTINEL] = _COOKIE_SENTINEL_VALUE

    def save_to_cookie(self, resp):
        if not 200 <= resp.status_code < 400:
            return
        self.set_sentinel()
        s = self._serialize()
        if s == self.incoming_serialized:
            return
        resp.set_cookie(
            cfg.http_name,
            self._encrypt(s),
            max_age=_MAX_AGE_SECONDS,
            httponly=True,
            secure=cfg.is_secure,
            #TODO(pjm): enabling this causes self-extracting simulations to break
            #samesite='Strict',
        )

    def _crypto(self):
        if not self.crypto:
            if cfg.private_key is None:
                assert pkconfig.channel_in('dev'), \
                    'must configure private_key in non-dev channel={}'.format(pkconfig.cfg.channel)
                cfg.private_key = base64.urlsafe_b64encode(b'01234567890123456789012345678912')
            assert len(base64.urlsafe_b64decode(cfg.private_key)) == 32, \
                'private_key must be 32 characters and encoded with urlsafe_b64encode'
            self.crypto = cryptography.fernet.Fernet(cfg.private_key)
        return self.crypto

    def _decrypt(self, value):
        d = self._crypto().decrypt(
            base64.urlsafe_b64decode(pkcompat.to_bytes(value)),
        )
        pkdc('{}', d)
        return pkcompat.from_bytes(d)

    def _deserialize(self, value):
        v = value.split(_SERIALIZER_SEP)
        v = dict(zip(v[::2], v[1::2]))
        assert v[_COOKIE_SENTINEL] == _COOKIE_SENTINEL_VALUE, \
            'cookie sentinel value is not correct'
        return v

    def _encrypt(self, text):
        return base64.urlsafe_b64encode(
            self._crypto().encrypt(pkcompat.to_bytes(text)),
        )

    def _from_cookie_header(self, header):
        s = None
        err = None
        try:
            match = re.search(
                r'\b{}=([^;]+)'.format(cfg.http_name),
                header,
            )
            if match:
                s = self._decrypt(match.group(1))
                self.update(auth_hook_from_header(self._deserialize(s)))
                self.incoming_serialized = s
                return
        except Exception as e:
            if 'crypto' in type(e).__module__:
                # cryptography module exceptions serialize to empty string
                # so just report the type.
                e = type(e)
            err = e
            pkdc('{}', pkdexc())
        if err:
            pkdlog('Cookie decoding failed: {} value={}', err, s)

    def _serialize(self):
        return _SERIALIZER_SEP.join(
            itertools.chain.from_iterable(
                [(k, self[k]) for k in sorted(self.keys())],
            ),
        )


@pkconfig.parse_none
def _cfg_http_name(value):
    assert re.search(r'^\w{1,32}$', value), \
        'must be 1-32 word characters; http_name={}'.format(value)
    return value


def _state():
    return sirepo.srcontext.get(_SRCONTEXT_KEY)


cfg = pkconfig.init(
    http_name=('sirepo_' + pkconfig.cfg.channel, _cfg_http_name, 'Set-Cookie name'),
    private_key=(None, str, 'urlsafe base64 encrypted 32-byte key'),
    is_secure=(
        not pkconfig.channel_in('dev'),
        pkconfig.parse_bool,
        'Add secure attriute to Set-Cookie',
    )
)
