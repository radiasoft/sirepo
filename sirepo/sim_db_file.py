# -*- coding: utf-8 -*-
"""Getting and putting simulation db files

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern import pkio
from pykern.pkdebug import pkdp, pkdlog
from pykern.pkcollections import PKDict
import re
import sirepo.job
import sirepo.simulation_db
import sirepo.tornado
import sirepo.util
import tornado.web

_AUTH_HEADER_RE = re.compile(
    sirepo.util.AUTH_HEADER_SCHEME_BEARER
    + r"\s("
    + sirepo.job.UNIQUE_KEY_CHARS_RE
    + ")",
    re.IGNORECASE,
)

# TODO(robnagler) figure out how to do in tornado, e.g. get path_info
_URI_RE = re.compile(f"^{sirepo.job.SIM_DB_FILE_URI}/(.+)")
_TOKEN_TO_UID = PKDict()
_UID_TO_TOKEN = PKDict()


class FileReq(tornado.web.RequestHandler):
    def delete(self, path):
        for f in pkio.sorted_glob(f"{self.__authenticated_path()}*"):
            pkio.unchecked_remove(f)

    def get(self, path):
        p = self.__authenticated_path()
        if not p.exists():
            raise sirepo.tornado.error_not_found()
        self.write(pkio.read_binary(p))

    def put(self, path):
        self.__authenticated_path().write_binary(self.request.body)

    def __authenticate(self):
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
        u = _TOKEN_TO_UID.get(m.group(1))
        if not u:
            pkdlog("token={} not found", m.group(1))
            raise sirepo.tornado.error_forbidden()
        return u

    def __authenticated_path(self):
        u = self.__authenticate()
        m = _URI_RE.search(self.request.path)
        if not m:
            pkdlog(
                "uri={} missing {sirepo.job.SIM_DB_FILE_URI} prefix", self.request.path
            )
            raise sirepo.tornado.error_forbidden()
        return sirepo.simulation_db.sim_db_file_uri_to_path(
            path=m.group(1),
            expect_uid=u,
        )


def token_for_user(uid):
    def _token():
        for _ in range(10):
            t = sirepo.job.unique_key()
            if t not in _TOKEN_TO_UID:
                _TOKEN_TO_UID[t] = uid
                return t
        raise AssertionError("should not happen: too many token collisions")

    return _UID_TO_TOKEN.pksetdefault(uid, _token)[uid]
