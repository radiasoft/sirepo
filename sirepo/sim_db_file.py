"""Getting and putting simulation db files

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern import pkconfig
from pykern import pkcompat
from pykern import pkio
from pykern import pkjson
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdlog, pkdexc
import re
import sirepo.agent_supervisor_api
import sirepo.const
import sirepo.job
import sirepo.template
import sirepo.tornado

_URI_RE = re.compile(f"^{sirepo.job.SIM_DB_FILE_URI}/(.+)")


def in_job_agent():
    return bool(_cfg.server_token)


class SimDbClient:
    """Client to be used from the job agent"""

    _EXE_PERMISSIONS = 0o700

    LIB_DIR = sirepo.const.LIB_DIR

    def __init__(self, sim_data):
        super().__init__()
        self._sim_data = sim_data

    def copy(self, src_uri, dst_uri):
        """Copy `src_uri` to `dst_uri`

        Args:
            src_uri (SimDbUri): from file
            dst_uri (SimDbUri): to file
        """
        return self._post("copy", src_uri, basename=None, args=PKDict(dst_uri=dst_uri))

    def delete_glob(self, lib_sid_uri, path_prefix, sim_type=None):
        """deletes files that begin with `path_prefix`"""
        return self._post("delete_glob", lib_sid_uri, path_prefix, sim_type=sim_type)

    def exists(self, lib_sid_uri, basename=None, sim_type=None):
        """Tests if file exists"""
        return self._post("exists", lib_sid_uri, basename, sim_type=sim_type)

    def get(self, lib_sid_uri, basename=None, sim_type=None):
        return self._request("GET", lib_sid_uri, basename, sim_type=sim_type).content

    def get_and_save(
        self, lib_sid_uri, basename, dest_dir, is_exe=False, sim_type=None
    ):
        p = dest_dir.join(basename)
        p.write_binary(self.get(lib_sid_uri, basename, sim_type=sim_type))
        if is_exe:
            p.chmod(self._EXE_PERMISSIONS)
        return p

    def move(self, src_uri, dst_uri):
        """Rename `src_uri` to `dst_uri`

        Args:
            src_uri (SimDbUri): from path
            dst_uri (SimDbUri): to path
        """
        return self._post("move", src_uri, basename=None, args=PKDict(dst_uri=dst_uri))

    def size(self, lib_sid_uri, basename=None, sim_type=None):
        return self._post("size", lib_sid_uri, basename, sim_type=sim_type)

    def uri(self, lib_sid_uri, basename=None, sim_type=None):
        """Create a `SimDbUri`

        ``lib_sid_uri`` may be `sirepo.const.LIB_DIR`, a simulation id, or a
        `SimDbUri`.  In the latter case, the uri must match ``sim_type``
        (if supplied), and ``basename`` must be None.

        Args:
            lib_sid_uri (object): see above
            basename (str): naem without directories (see above)
            sim_type (str): valid code [sim_data.sim_type]
        Returns:
            SimDbUri: valid in any string context
        """
        return SimDbUri(sim_type or self._sim_data.sim_type(), lib_sid_uri, basename)

    def write(self, lib_sid_uri, basename, path_or_content, sim_type=None):
        def _data():
            if isinstance(path_or_content, pkconst.PY_PATH_LOCAL_TYPE):
                return pkio.read_binary(path_or_content)
            return pkcompat.to_bytes(path_or_content)

        return self._request(
            "PUT", lib_sid_uri, basename, data=_data(), sim_type=sim_type
        )

    def _post(self, method, lib_sid_uri, basename, args=None, sim_type=None):
        res = pkjson.load_any(
            self._request(
                "POST",
                lib_sid_uri,
                basename,
                json=PKDict(method=method, args=PKDict() if args is None else args),
                sim_type=sim_type,
            ).content,
        )
        if res.get("state") != "ok":
            raise AssertionError(
                "expected state=ok reply={} uri={} basename={}", res, basename
            )
        return res.result

    def _request(
        self, method, lib_sid_uri, basename, data=None, json=None, sim_type=None
    ):
        u = self.uri(lib_sid_uri, basename, sim_type)
        r = sirepo.agent_supervisor_api.request(
            method,
            _cfg.server_uri + u,
            _cfg.server_token,
            data=data,
            json=json,
        )
        if r.status_code == 404:
            raise FileNotFoundError(f"sim_db_file={u} not found")
        r.raise_for_status()
        return r


class SimDbServer(sirepo.agent_supervisor_api.ReqBase):
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
        from sirepo import simulation_db

        sirepo.template.assert_sim_type(stype),
        _sid_or_lib(sid_or_lib),
        simulation_db.assert_sim_db_basename(basename),
        return simulation_db.user_path_root().join(
            self.__uid, stype, sid_or_lib, basename
        )


class SimDbUri(str):
    def __new__(cls, sim_type, slu, basename):

        if isinstance(slu, cls):
            if basename is not None:
                raise AssertionError(
                    f"basename={basename} must be none when uri={slu} supplied"
                )
            if sim_type != slu._stype:
                raise AssertionError(f"sim_type={sim_type} disagrees with uri={slu}")
            return slu
        self = super(cls).__new__(cls.uri_from_parts(sim_type, sid_or_lib, basename))
        self._stype = sim_type
        return self

    @classmethod
    def _uri_from_parts(cls, sim_type, sid_or_lib, basename):
        """Generate relative URI for path

        Args:
            sim_type (str): which code
            sid_or_lib (str): simulation id. if None or `_LIB_DIR`, is library file
            basename (str): file name with extension

        Returns:
            str: uri to be passed to SimDbClient functions
        """

        return "/".join(
            [
                sirepo.template.assert_sim_type(sim_type),
                _sid_or_lib(sid_or_lib),
                assert_sim_db_basename(basename),
            ]
        )


def _sid_or_lib(value):
    return _LIB_DIR if value is None or value == _LIB_DIR else assert_sid(value)


_cfg = pkconfig.init(
    server_token=(None, str, "credential to connect"),
    server_uri=(None, str, "how to connect to server"),
)
