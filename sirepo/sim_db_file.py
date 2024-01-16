"""Getting and putting simulation db files

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern import pkio
from pykern import pkjson
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdlog, pkdexc
import re
import sirepo.agent_supervisor_api
import sirepo.job
import sirepo.simulation_db
import sirepo.tornado

_URI_RE = re.compile(f"^{sirepo.job.SIM_DB_FILE_URI}/(.+)")


class FileReq(sirepo.agent_supervisor_api.ReqBase):
    _TOKEN_TO_UID = PKDict()
    _UID_TO_TOKEN = PKDict()

    def get(self, unused_arg):
        p = self.__authenticate_and_path()
        if not p.exists():
            raise sirepo.tornado.error_not_found()
        self.write(pkio.read_binary(p))

    async def post(self, unused_arg):
        try:
            r = pkjson.load_any(self.request.body)
            a = r.get("args")
            # note that args may be empty, since uri has path
            if not isinstance(a, PKDict):
                raise AssertionError(f"invalid post args={a}")
            self.__path = self.__authenticate_and_path()
            self.write(
                getattr(self, "_sr_post_" + r.get("method", "missing_method"))(a)
            )
        except Exception as e:
            if pkio.exception_is_not_found(e):
                raise sirepo.tornado.error_not_found()
            pkdlog(
                "uri={} body={} exception={} stack={}",
                self.request.path,
                self.request.body,
                e,
                pkdexc(),
            )
            try:
                self.write({state: "error"})
            except Exception:
                pass

    def put(self, unused_arg):
        self.__authenticate_and_path().write_binary(self.request.body)

    def __authenticate_and_path(self):
        self.__uid = self._rs_authenticate()
        return self.__uri_to_path(self.request.path)

    def _sr_post_delete_glob(self, args):
        t = []
        for f in pkio.sorted_glob(f"{self.__authenticate_and_path()}*"):
            if f.check(dir=True):
                pkdlog("path={} is a directory", f)
                raise sirepo.tornado.error_forbidden()
            t.append(f)
        for f in t:
            pkio.unchecked_remove(f)

    def _sr_post_copy(self, args):
        self._path.copy(self.__uri_to_path(self.args.dst_uri))
        return PKDict(state="ok")

    def _sr_post_exists(self, args):
        return PKDict(state="ok", result=self._path.check(file=True))

    def _sr_post_move(self, args):
        self._path.move(self.__uri_to_path(self.args.dst_uri))
        return PKDict(state="ok")

    def _sr_post_size(self, args):
        return PKDict(state="ok", result=self._path.size())

    def _sr_post_missing_method(self, args):
        raise AssertionError("missing method path={} args={}", self._path, args)

    def __uri_to_path(self, uri):
        m = _URI_RE.search(uri)
        if not m:
            pkdlog("uri={} missing {sirepo.job.SIM_DB_FILE_URI} prefix", uri)
            raise sirepo.tornado.error_forbidden()
        return sirepo.simulation_db.sim_db_file_uri_to_path(
            uri=m.group(1),
            expect_uid=self.__uid,
        )
