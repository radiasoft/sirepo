"""User state management via an HTTP cookie

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern import pkcompat
from pykern import pkconfig
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp
import base64
import copy
import cryptography.fernet
import itertools
import re
import sirepo.events
import sirepo.quest
import sirepo.util

#: Identifies if the cookie has been returned at least once by the client
_COOKIE_SENTINEL = "srk"

#: Unique, truthy that can be asserted on decrypt
_COOKIE_SENTINEL_V2 = "2"

#: Old value, which will get rewritten on first request, removing httponlya
_COOKIE_SENTINEL_V1 = "z"

#: Valid sentinel values
_COOKIE_SENTINEL_VERSIONS = frozenset((_COOKIE_SENTINEL_V1, _COOKIE_SENTINEL_V2))

_HTTP_HEADER_ADD_FMT = None

_HTTP_HEADER_ADD_BASE = f"Max-Age={10 * 365 * 24 * 3600}; Path=/; SameSite=Lax"

#: See description in `reply.delete_third_party_cookies`
_HTTP_HEADER_DELETE_FMT = "{key}=; Max-Age=0; Path={path}"

_SERIALIZER_SEP = " "

_cfg = None


def init_quest(qcall):
    c = _Cookie(qcall)
    if qcall.bucket_unchecked_get("in_pkcli"):
        c.set_sentinel()


def unchecked_http_name():
    """http_name used in the cookie header

    Should only be called by `sirepo.auth`.

    Returns:
       str: http_name or None
    """
    return _cfg and _cfg.http_name


class _Cookie(sirepo.quest.Attr):
    # Only necessary to cascade values
    _INIT_QUEST_FOR_CHILD_KEYS = frozenset(("_values",))

    def __init__(self, qcall, *args, **kwargs):
        super().__init__(qcall, *args, **kwargs)
        self._modified = False
        if kwargs.get("init_quest_for_child"):
            return
        s = qcall.sreq.cookie_state
        if isinstance(s, PKDict):
            self._values = s
        else:
            # Also handles case where state is None (_SRequestCLI)
            self._from_http_header(qcall, s)

    def export_state(self):
        """Persistent state for next websocket call

        Returns:
            object: anonymous values to be passed to init_quest
        """
        return self._values

    def get_value(self, key):
        return self._values[key]

    def has_key(self, key):
        return key in self._values

    def has_sentinel(self):
        return _COOKIE_SENTINEL in self._values

    def http_header_values(self, to_delete=tuple()):
        """Returns values to be used in http cookie set headers

        Always returns `self` serialized. Also returns serialized
        `to_delete`.

        This call only happens if `save_to_reply` has called `_SReply.cookie_set`.

        Args:
            cookies_to_delete (iter): optional headers to create

        Returns:
            tuple: values to be passed to Set-Cookie

        """
        return (_HTTP_HEADER_ADD_FMT.format(self._encrypt(self._serialize())),) + tuple(
            _HTTP_HEADER_DELETE_FMT.format(**v) for v in to_delete
        )

    def reset_state(self, error):
        """Clear all values and log `error` with values.

        Args:
            error (str): to be logged
        """
        pkdlog("resetting cookie: error={} values={}", error, self._values)
        self._modified = True
        self._values.clear()

    def save_to_reply(self, resp):
        if not self._modified:
            return
        self._modified = False
        self.set_sentinel()
        resp.cookie_set(self)

    def set_sentinel(self):
        self._modified = True
        self._values[_COOKIE_SENTINEL] = _COOKIE_SENTINEL_V2

    def set_value(self, key, value):
        v = str(value)
        assert (
            not _SERIALIZER_SEP in v
        ), f"value={v} must not contain _SERIALIZER_SEP={_SERIALIZER_SEP}"
        assert (
            key != _COOKIE_SENTINEL
        ), f"key={key} is _COOKIE_SENTINEL={_COOKIE_SENTINEL}"
        assert (
            _COOKIE_SENTINEL in self._values
        ), f"_COOKIE_SENTINEL not set self keys={sorted(self._values.keys())} for key={key}"
        self._modified = True
        self._values[key] = v

    def unchecked_get_value(self, key, default=None):
        return self._values.get(key, default)

    def unchecked_remove(self, key):
        self._modified = True
        return self._values.pkdel(key)

    def _crypto(self):
        if "_crypto_alg" not in self:
            if _cfg.private_key is None:
                assert pkconfig.in_dev_mode(), "must configure private_key in non-dev"
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
        v = PKDict(zip(v[::2], v[1::2]))
        if v[_COOKIE_SENTINEL] not in _COOKIE_SENTINEL_VERSIONS:
            raise AssertionError(
                f"cookie sentinel value={v[_COOKIE_SENTINEL]} is invalid",
            )
        if v[_COOKIE_SENTINEL] in _COOKIE_SENTINEL_V1:
            self._modified = True
            v[_COOKIE_SENTINEL_V1] = _COOKIE_SENTINEL_V2
        return v

    def _encrypt(self, text):
        return pkcompat.from_bytes(
            base64.urlsafe_b64encode(
                self._crypto().encrypt(pkcompat.to_bytes(text)),
            ),
        )

    def _from_http_header(self, qcall, header):
        def _parse():
            s = None
            try:
                m = re.search(
                    rf"\b{_cfg.http_name}=([^;]+)",
                    header,
                )
                if m:
                    s = self._decrypt(m.group(1))
                    self._values, m = qcall.auth.cookie_cleaner(self._deserialize(s))
                    if m:
                        self._modified = True
                    return True
            except Exception as e:
                if "crypto" in type(e).__module__:
                    # cryptography module exceptions serialize to empty string
                    # so just report the type.
                    e = type(e)
                pkdc("{}", pkdexc())
                pkdlog("Cookie decoding error={} value={}", e, s)
            return False

        if header and _parse():
            return
        self._modified = True
        self._values = PKDict()

    def _serialize(self):
        return _SERIALIZER_SEP.join(
            itertools.chain.from_iterable(
                [(k, self._values[k]) for k in sorted(self._values.keys())],
            ),
        )


@pkconfig.parse_none
def _cfg_http_name(value):
    assert re.search(
        r"^\w{1,32}$", value
    ), "must be 1-32 word characters; http_name={}".format(value)
    return value


def _end_api_call(qcall, kwargs):
    qcall.cookie.save_to_reply(kwargs.resp)


def init_module():
    global _cfg, _HTTP_HEADER_ADD_FMT

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
            not pkconfig.in_dev_mode(),
            pkconfig.parse_bool,
            "Add secure attribute to Set-Cookie",
        ),
    )

    # SECURITY: We set cookies via Javascript so httponly must be false.
    # We do not inject second party HTML. XSS is unlikely.
    _HTTP_HEADER_ADD_FMT = (
        _cfg.http_name
        + "={}; "
        + _HTTP_HEADER_ADD_BASE
        + ("; Secure" if _cfg.is_secure else "")
    )
    sirepo.events.register(PKDict(end_api_call=_end_api_call))
