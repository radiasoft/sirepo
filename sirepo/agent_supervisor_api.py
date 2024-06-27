"""Utilities for agent to supervisor api requests

For example, sim_db_file and global_resources.

:copyright: Copyright (c) 2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdlog, pkdp, pkdexc
import requests
import sirepo.http_util
import sirepo.job
import sirepo.tornado
import sirepo.util


class ReqBase(sirepo.tornado.AuthHeaderRequestHandler):
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

    def write_error(self, *args, **kwargs):
        if e := kwargs.get("exc_info"):
            pkdlog("exception={} stack={}", e[1], pkdexc(e))
        super().write_error(*args, **kwargs)

    def _rs_authenticate(self, *args, **kwargs):
        m = super()._rs_authenticate(self, *args, **kwargs)
        u = self._TOKEN_TO_UID.get(m)
        if not u:
            pkdlog("token={} not found", m)
            raise sirepo.tornado.error_forbidden()
        return u


def request(method, uri, token, data=None, json=None):
    _check_size(method, data)
    return requests.request(
        method,
        uri,
        json=json,
        data=data,
        verify=sirepo.job.cfg().verify_tls,
        headers=sirepo.http_util.auth_header(token),
    )


def _check_size(method, data):
    m = sirepo.job.cfg().max_message_bytes
    if data and len(data) > m:
        raise sirepo.util.ContentTooLarge(
            f"len(data)={len(data)} > max_size={m} for method={method}"
        )
