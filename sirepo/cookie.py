# -*- coding: utf-8 -*-
"""User state management via an HTTP cookie

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern import pkcompat
from pykern import pkconfig
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp
import base64
import cryptography.fernet
import itertools
import re
import sirepo.events
import sirepo.quest
import sirepo.util

_MAX_AGE_SECONDS = 10 * 365 * 24 * 3600

#: Identifies if the cookie has been returned at least once by the client
_COOKIE_SENTINEL = "srk"

#: Unique, truthy that can be asserted on decrypt
_COOKIE_SENTINEL_VALUE = "z"

_SERIALIZER_SEP = " "

_cfg = None


def init_quest(qcall):
    qcall.attr_set("cookie", _Cookie(qcall))


class _Cookie(sirepo.quest.Attr):
    def __init__(self, qcall):
        super().__init__()
        self.__incoming_serialized = ""
        self._from_cookie_header(qcall)

    def get_value(self, key):
        return self.__values[key]

    def has_key(self, key):
        return key in self.__values

    def has_sentinel(self):
        return _COOKIE_SENTINEL in self.__values

    def reset_state(self, error):
        """Clear all values and log `error` with values.

        Args:
            error (str): to be logged
        """
        pkdlog("resetting cookie: error={} values={}", error, _state())
        self.__values.clear()

    def save_to_cookie(self, resp):
        if not 200 <= resp.status_code < 400:
            return
        self.set_sentinel()
        s = self._serialize()
        if s == self.__incoming_serialized:
            return
        resp.set_cookie(
            _cfg.http_name,
            self._encrypt(s),
            max_age=_MAX_AGE_SECONDS,
            httponly=True,
            secure=_cfg.is_secure,
            samesite="Lax",
        )

    def set_sentinel(self):
        self.__values[_COOKIE_SENTINEL] = _COOKIE_SENTINEL_VALUE

    def set_value(self, key, value):
        value = str(value)
        assert (
            not _SERIALIZER_SEP in value
        ), 'value must not container serializer sep "{}"'.format(_SERIALIZER_SEP)
        assert (
            key == _COOKIE_SENTINEL or _COOKIE_SENTINEL in self.__values
        ), "key={} is _COOKIE_SENTINEL={_COOKIE_SENTINEL} or exist in self".format(key)
        self.__values[key] = value

    def unchecked_get_value(self, key, default=None):
        return self.__values.get(key, default)

    def unchecked_remove(self, key):
        return self.__values.pkdel(key)

    def _crypto(self):
        if "_crypto_alg" not in self:
            if _cfg.private_key is None:
                assert pkconfig.channel_in(
                    "dev"
                ), "must configure private_key in non-dev channel={}".format(
                    pkconfig.cfg.channel
                )
                _cfg.private_key = base64.urlsafe_b64encode(
                    b"01234567890123456789012345678912"
                )
            assert (
                len(base64.urlsafe_b64decode(_cfg.private_key)) == 32
            ), "private_key must be 32 characters and encoded with urlsafe_b64encode"
            self._crypto_alg = cryptography.fernet.Fernet(_cfg.private_key)
        return self._crypto_alg

    def _decrypt(self, value):
        d = self._crypto().decrypt(
            base64.urlsafe_b64decode(pkcompat.to_bytes(value)),
        )
        pkdc("{}", d)
        return pkcompat.from_bytes(d)

    def _deserialize(self, value):
        v = value.split(_SERIALIZER_SEP)
        v = dict(zip(v[::2], v[1::2]))
        assert (
            v[_COOKIE_SENTINEL] == _COOKIE_SENTINEL_VALUE
        ), "cookie sentinel value is not correct"
        return v

    def _encrypt(self, text):
        return base64.urlsafe_b64encode(
            self._crypto().encrypt(pkcompat.to_bytes(text)),
        )

    def _from_cookie_header(self, qcall):
        header = qcall.sreq.header_uget("Cookie")
        self.__values = PKDict()
        if not header:
            return
        s = None
        err = None
        try:
            match = re.search(
                r"\b{}=([^;]+)".format(_cfg.http_name),
                header,
            )
            if match:
                s = self._decrypt(match.group(1))
                self.__values.update(qcall.auth.cookie_cleaner(self._deserialize(s)))
                self.__incoming_serialized = s
                return
        except Exception as e:
            if "crypto" in type(e).__module__:
                # cryptography module exceptions serialize to empty string
                # so just report the type.
                e = type(e)
            err = e
            pkdc("{}", pkdexc())
        if err:
            pkdlog("Cookie decoding failed: {} value={}", err, s)

    def _serialize(self):
        return _SERIALIZER_SEP.join(
            itertools.chain.from_iterable(
                [(k, self.__values[k]) for k in sorted(self.__values.keys())],
            ),
        )


@pkconfig.parse_none
def _cfg_http_name(value):
    assert re.search(
        r"^\w{1,32}$", value
    ), "must be 1-32 word characters; http_name={}".format(value)
    return value


def _end_api_call(qcall, kwargs):
    qcall.cookie.save_to_cookie(kwargs.resp)


def init_module():
    global _cfg

    if _cfg:
        return
    _cfg = pkconfig.init(
        http_name=(
            "sirepo_" + pkconfig.cfg.channel,
            _cfg_http_name,
            "Set-Cookie name",
        ),
        private_key=(None, str, "urlsafe base64 encrypted 32-byte key"),
        is_secure=(
            not pkconfig.channel_in("dev"),
            pkconfig.parse_bool,
            "Add secure attriute to Set-Cookie",
        ),
    )
    sirepo.events.register(PKDict(end_api_call=_end_api_call))
