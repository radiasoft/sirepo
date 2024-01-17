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


def uri_from_parts(sim_type, sid_or_lib, basename):
    """Generate relative URI for path

    Args:
        sim_type (str): which code
        sid_or_lib (str): simulation id. if None or `_LIB_DIR`, is library file
        basename (str): file name with extension

    Returns:
        str: uri to be passed to sim_db_file functions
    """

    return "/".join(
        [
            sirepo.template.assert_sim_type(sim_type),
            _sid_or_lib(sid_or_lib),
            assert_sim_db_basename(basename),
        ]
    )


class FileReq(sirepo.agent_supervisor_api.ReqBase):
    _TOKEN_TO_UID = PKDict()
    _UID_TO_TOKEN = PKDict()

    def get(self, unused_arg):
        p = self.__authenticate_and_path()
        if not p.exists():
            raise sirepo.tornado.error_not_found()
        self.write(pkio.read_binary(p))

    async def post(self, unused_arg):
        def _result(value):
            if value is None:
                value = PKDict()
            elif not isinstance(value, PKDict):
                value = PKDict(result=value)
            return value.pksetdefault(state="ok")

        try:
            a = pkjson.load_any(self.request.body).get("args")
            # note that args may be empty (but must be PKDict), since uri has path
            if not isinstance(a, PKDict):
                raise AssertionError(f"invalid post args={a}")
            self.__path = self.__authenticate_and_path()
            self.write(
                _result(
                    getattr(self, "_sr_post_" + r.get("method", "missing_method"))(a),
                ),
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
        self._path.copy(self.__uri_to_path_simple(self.__uri_arg_to_path(args.dst_uri)))

    def _sr_post_exists(self, args):
        return self._path.check(file=True)

    def _sr_post_move(self, args):
        self._path.move(self.__uri_to_path_simple(self.__uri_arg_to_path(args.dst_uri)))

    def _sr_post_size(self, args):
        return self._path.size()

    def _sr_post_missing_method(self, args):
        raise AssertionError("missing method path={} args={}", self._path, args)

    def __authenticate_and_path(self):
        self.__uid = self._rs_authenticate()
        return self.__uri_to_path(self.request.path)

    def __uri_arg_to_path(self, uri):
        p = uri.split("/")
        if len(p) != 3:
            raise AssertionError(f"uri={p} must be 3 parts")
        return self.__uri_to_path_simple(*p)

    def __uri_to_path(self, uri):
        m = _URI_RE.search(uri)
        if not m:
            pkdlog("uri={} missing {sirepo.job.SIM_DB_FILE_URI} prefix", uri)
            raise sirepo.tornado.error_forbidden()
        p = m.group(1).split("/")
        assert len(p) == 4, f"uri={p} must be 4 parts"
        assert p[0] == self.__uid, f"uid={p[0]} is not expect_uid={self.__uid}"
        return self.__uri_to_path_simple(*p[1:])

    def __uri_to_path_simple(self, stype, sid_or_lib, basename):
        sirepo.template.assert_sim_type(stype),
        _sid_or_lib(sid_or_lib),
        sirepo.simulation_db.assert_sim_db_basename(basename),
        return simulation_db.user_path_root().join(
            self.__uid, stype, sid_or_lib, basename
        )


def _sid_or_lib(value):
    return _LIB_DIR if value is None or value == _LIB_DIR else assert_sid(value)
