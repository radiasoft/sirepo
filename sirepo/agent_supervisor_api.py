"""Utilities for agent to supervisor api requests

For example, sim_db_file and global_resources.

:copyright: Copyright (c) 2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdlog, pkdp, pkdexc
import re
import requests
import sirepo.job
import sirepo.util
import tornado.web

#: prefix for auth header of requests
_AUTH_HEADER_PREFIX = f"{sirepo.util.AUTH_HEADER_SCHEME_BEARER} "

#: Regex to test format of auth header and extract token
_AUTH_HEADER_RE = re.compile(
    sirepo.util.AUTH_HEADER_SCHEME_BEARER
    + r"\s("
    + sirepo.job.UNIQUE_KEY_CHARS_RE
    + ")",
    re.IGNORECASE,
)


class ReqBase(tornado.web.RequestHandler):
    @classmethod
    def token_for_user(cls, uid):
        def _token():
            for _ in range(10):
                t = sirepo.job.unique_key()
                if t not in cls._TOKEN_TO_UID:
                    cls._TOKEN_TO_UID[t] = uid
                    return t
            raise AssertionError("should not happen: too many token collisions")

        return cls._UID_TO_TOKEN.pksetdefault(uid, _token)[uid]

    def _rs_authenticate(self, *args, **kwargs):
        t = self.request.headers.get(sirepo.util.AUTH_HEADER)
        if not t:
            raise sirepo.tornado.error_forbidden()
        p = t.split(" ")
        if len(p) != 2:
            raise sirepo.tornado.error_forbidden()
        m = _AUTH_HEADER_RE.search(t)
        if not m:
            pkdlog("invalid auth header={}", t)
            raise sirepo.tornado.error_forbidden()
        u = self._TOKEN_TO_UID.get(m.group(1))
        if not u:
            pkdlog("token={} not found", m.group(1))
            raise sirepo.tornado.error_forbidden()
        return u

    def write_error(self, *args, **kwargs):
        if e := kwargs.get("exc_info"):
            pkdlog("exception={} stack={}", e[1], pkdexc(e))
        super().write_error(*args, **kwargs)


def request(method, uri, token, data=None, json=None):
    _check_size(method, data)
    return requests.request(
        method,
        uri,
        json=json,
        data=data,
        verify=sirepo.job.cfg().verify_tls,
        headers=PKDict(
            {
                sirepo.util.AUTH_HEADER: _AUTH_HEADER_PREFIX + token,
            }
        ),
    )


def _check_size(method, data):
    m = sirepo.job.cfg().max_message_bytes
    if data and len(data) > m:
        raise sirepo.util.ContentTooLarge(
            f"len(data)={len(data)} > max_size={m} for method={method}"
        )
