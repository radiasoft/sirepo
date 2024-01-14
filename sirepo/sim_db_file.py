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

# TODO(robnagler) figure out how to do in tornado, e.g. get path_info
_URI_RE = re.compile(f"^{sirepo.job.SIM_DB_FILE_URI}/(.+)")


class FileReq(sirepo.agent_supervisor_api.ReqBase):
    _TOKEN_TO_UID = PKDict()
    _UID_TO_TOKEN = PKDict()

    def delete(self, unused_arg):
        # TODO(robnagler) This is too coarse change to a POST
        t = []
        for f in pkio.sorted_glob(f"{self.__authenticated_path()}*"):
            if not f.check(file=True):
                pkdlog("path={} is a directory", f)
                raise sirepo.tornado.error_forbidden()
            t.append(f)
        for f in t:
            pkio.unchecked_remove(f)

    def get(self, unused_arg):
        p = self.__authenticated_path()
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
            a.path = self.__authenticated_path()
            self.write(getattr(self, "_post_" + r.get("method", "missing_method"))(a))
        except Exception as e:
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
        self.__authenticated_path().write_binary(self.request.body)

    def __authenticated_path(self):
        u = self._rs_authenticate()
        m = _URI_RE.search(self.request.path)
        if not m:
            pkdlog(
                "uri={} missing {sirepo.job.SIM_DB_FILE_URI} prefix", self.request.path
            )
            raise sirepo.tornado.error_forbidden()
        return sirepo.simulation_db.sim_db_file_uri_to_path(
            uri=m.group(1),
            expect_uid=u,
        )

    def _post_exists(self, args):
        return PKDict(state="ok", result=args.path.check(file=True))

    def _post_missing_method(self, args):
        raise AssertionError("missing method args={}", args)
