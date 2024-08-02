"""Operating on simulation db files via the job agent

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern import pkcompat
from pykern import pkconfig
from pykern import pkconst
from pykern import pkinspect
from pykern import pkio
from pykern import pkjson
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdlog, pkdexc
import aiofiles
import aiohttp
import re
import sirepo.agent_supervisor_api
import sirepo.const
import sirepo.job
import sirepo.tornado
import sirepo.util
import socket

_URI_RE = re.compile(f"^{sirepo.job.SIM_DB_FILE_URI}/(.+)")
_CHUNK_SIZE = 1024 * 1024


def in_job_agent():
    return bool(_cfg.server_token)


class SimDbClient:
    """Client to be used from the job agent.

    An instance is created and is accessed via `SimData.sim_db_client`.
    """

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
        self._post(src_uri, basename=None, args=PKDict(dst_uri=dst_uri))

    def delete_glob(self, lib_sid_uri, path_prefix, sim_type=None):
        """deletes files that begin with `path_prefix`"""
        self._post(lib_sid_uri, path_prefix, sim_type=sim_type)

    def exists(self, lib_sid_uri, basename=None, sim_type=None):
        """Tests if file exists"""
        return self._post(lib_sid_uri, basename, sim_type=sim_type)

    def get(self, lib_sid_uri, basename=None, sim_type=None):
        return self._request("GET", lib_sid_uri, basename, sim_type=sim_type).content

    def move(self, src_uri, dst_uri):
        """Rename `src_uri` to `dst_uri`

        Args:
            src_uri (SimDbUri): from path
            dst_uri (SimDbUri): to path
        """
        self._post(src_uri, basename=None, args=PKDict(dst_uri=dst_uri))

    def put(self, lib_sid_uri, basename, path_or_content, sim_type=None):
        def _data():
            if isinstance(path_or_content, pkconst.PY_PATH_LOCAL_TYPE):
                return pkio.read_binary(path_or_content)
            return pkcompat.to_bytes(path_or_content)

        self._request("PUT", lib_sid_uri, basename, data=_data(), sim_type=sim_type)

    def read_sim(self, lib_sid_uri, sim_type=None):
        return self._post(
            lib_sid_uri,
            basename=sirepo.const.SIM_DATA_BASENAME,
            sim_type=sim_type,
        )

    def save_from_url(self, src_url, dst_uri):
        self._post(dst_uri, args=PKDict(src_url=src_url))

    def save_sim(self, sdata):
        return self._post(
            sdata.models.simulation.simulationId,
            basename=sirepo.const.SIM_DATA_BASENAME,
            sim_type=sdata.simulationType,
            args=PKDict(sdata=sdata),
        )

    def size(self, lib_sid_uri, basename=None, sim_type=None):
        return self._post(lib_sid_uri, basename, sim_type=sim_type)

    def uri(self, lib_sid_uri, basename=None, sim_type=None):
        """Create a `SimDbUri`

        ``lib_sid_uri`` may be `sirepo.const.LIB_DIR`, a simulation id, or a
        `SimDbUri`.  In the latter case, the uri must match ``sim_type``
        (if supplied), and ``basename`` must be None (or match uri).

        Args:
            lib_sid_uri (object): see above
            basename (str): naem without directories (see above)
            sim_type (str): valid code [sim_data.sim_type]
        Returns:
            SimDbUri: valid in any string context
        """
        return SimDbUri(sim_type or self._sim_data.sim_type(), lib_sid_uri, basename)

    def _post(self, lib_sid_uri, basename=None, args=None, sim_type=None):
        res = pkjson.load_any(
            self._request(
                "POST",
                lib_sid_uri,
                basename,
                json=PKDict(
                    method=pkinspect.caller_func_name(),
                    args=PKDict() if args is None else args,
                ),
                sim_type=sim_type,
            ).content,
        )
        if res.get("state") != "ok":
            raise AssertionError(
                "expected state=ok reply={} uri={} basename={}", res, basename
            )
        return res.get("result")

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

    def _sr_authenticate(self, token, *args, **kwargs):
        self.__uid = super()._sr_authenticate(token, *args, **kwargs)
        p = _uri_parse(self.request.path, uid=self.__uid)
        if p is None:
            raise sirepo.tornado.error_forbidden()
        self.__uri_parts = p
        return p.path

    async def _sr_get(self, path, *args, **kwargs):
        if path.exists():
            self.write(pkio.read_binary(path))
        else:
            raise sirepo.tornado.error_not_found()

    async def _sr_post(self, path, *args, **kwargs):
        def _result(value):
            return PKDict(result=value).pksetdefault(state="ok")

        try:
            r = pkjson.load_any(self.request.body)
            # note that args may be empty (but must be PKDict), since uri has path
            if not isinstance(a := r.get("args"), PKDict):
                raise AssertionError(f"invalid post path={path} args={a}")
            if not (m := r.get("method")):
                raise AssertionError(f"missing method path={path} args={a}")
            self.write(_result(await getattr(self, "_sr_post_" + m)(path, a)))
        except Exception as e:
            if pkio.exception_is_not_found(e) or isinstance(
                e, sirepo.util.SPathNotFound
            ):
                raise sirepo.tornado.error_not_found()
            pkdlog(
                "uri={} body={} exception={} stack={}",
                self.request.path,
                self.request.body,
                e,
                pkdexc(),
            )
            self.write({state: "error"})

    async def _sr_post_delete_glob(self, path, args):
        t = []
        for f in pkio.sorted_glob(f"{path}*"):
            if f.check(dir=True):
                pkdlog("path={} is a directory", f)
                raise sirepo.tornado.error_forbidden()
                return
            t.append(f)
        for f in t:
            pkio.unchecked_remove(f)

    async def _sr_post_copy(self, path, args):
        p = self.__uri_arg_to_path(args.dst_uri)
        if not p:
            return
        # TODO(robnagler) should this be atomic?
        path.copy(p)

    async def _sr_post_exists(self, path, args):
        return path.check(file=True)

    async def _sr_post_move(self, path, args):
        p = self.__uri_arg_to_path(args.dst_uri)
        if not p:
            return
        path.move(p)

    async def _sr_post_read_sim(self, path, args):
        from sirepo import quest, simulation_db

        with quest.start() as qcall:
            with qcall.auth.logged_in_user_set(self.__uid):
                return simulation_db.read_simulation_json(
                    self.__uri_parts.sim_type,
                    self.__uri_parts.sid_or_lib,
                    qcall=qcall,
                )

    async def _sr_post_save_from_url(self, path, args):
        max_size = sirepo.job.cfg().max_message_bytes
        size = 0
        ok = False
        # so update is atomic
        t = path + ".tmp"
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get(args.src_url) as r:
                    if r.status != 200:
                        if r.status == 404:
                            return PKDict(error="not found")
                        return PKDict(error=f"http_status={response.status}")
                    async with aiofiles.open(t, "wb") as f:
                        async for c in r.content.iter_chunked(_CHUNK_SIZE):
                            size += len(c)
                            if size > max_size:
                                return PKDict(error=f"too large (max={max_size})")
                            await f.write(c)
            ok = True
        except Exception as e:
            pkdlog("url={} exc={} stack={}", args.src_url, e, pkdexc())
            if isinstance(e, socket.gaierror):
                return PKDict(error="invalid host")
            return PKDict(error=e)
        finally:
            if ok:
                t.move(path)
            else:
                pkio.unchecked_remove(t)
        return PKDict(size=size)

    async def _sr_post_save_sim(self, path, args):
        from sirepo import quest, simulation_db

        with quest.start() as qcall:
            with qcall.auth.logged_in_user_set(self.__uid):
                return simulation_db.save_simulation_json(
                    args.sdata,
                    fixup=True,
                    qcall=qcall,
                    modified=True,
                )

    async def _sr_post_size(self, path, args):
        return path.size()

    async def _sr_put(self, path):
        # TODO(e-carlin): check length of path and size of body
        async with aiofiles.open(path, "wb") as f:
            await f.write(self.request.body)

    def __uri_arg_to_path(self, uri):
        res = _uri_parse(uri, uid=self.__uid, is_arg_uri=True)
        if res is None:
            raise sirepo.tornado.error_forbidden()
        return res.path


class SimDbUri(str):
    """Identifies the relative path to a file in the simulation db.

    The value is a URI comprised of parts: sim_type, sim_id or
    `LIB_DIR` and basename.

    If `slu` is a `SimDbUri`, `basename` must match it or be None. `sim_type` must match the SimDbUri.

    Args:
        sim_type (str): simulation code
        slu (object): a SimDbUri, `LIB_DIR`, or a sim_id
        basename (str): valid simple file name
    """

    def __new__(cls, sim_type, slu, basename):
        if isinstance(slu, cls):
            if basename is not None and basename != slu._basename:
                raise AssertionError(
                    f"basename={basename} must be None or same as when uri={slu} supplied"
                )
            if sim_type != slu._sim_type:
                raise AssertionError(f"sim_type={sim_type} disagrees with uri={slu}")
            return slu
        self = super().__new__(cls, cls._uri_from_parts(sim_type, slu, basename))
        self._sim_type = sim_type
        self._basename = basename
        return self

    @classmethod
    def _uri_from_parts(cls, sim_type, sid_or_lib, basename):
        """Generate relative URI for path

        Args:
            sim_type (str): which code
            sid_or_lib (str): simulation id. if None or `LIB_DIR`, is library file
            basename (str): file name with extension

        Returns:
            str: uri to be passed to SimDbClient functions
        """
        from sirepo import simulation_db, template

        return "/".join(
            [
                template.assert_sim_type(sim_type),
                _sid_or_lib(sid_or_lib),
                simulation_db.assert_sim_db_basename(basename),
            ]
        )


def _sid_or_lib(value):
    from sirepo import simulation_db

    return (
        sirepo.const.LIB_DIR
        if value is None or value == sirepo.const.LIB_DIR
        else simulation_db.assert_sid(value)
    )


def _uri_parse(uri, uid, is_arg_uri=False):
    """Evaluate uri matches correct form and uid

    Separate function for testability

    Args:
        uri (str): to test
        uid (str): expected user
        is_arg_uri (bool): True then do not test uid
    Returns:
        PKDict: parts (path, sid_or_lib, sim_type, basename). None if error
    """

    def _result(sim_type, sid_or_lib, basename):
        from sirepo import simulation_db, template

        try:
            res = PKDict(
                basename=simulation_db.assert_sim_db_basename(basename),
                sid_or_lib=_sid_or_lib(sid_or_lib),
                sim_type=template.assert_sim_type(sim_type),
            )
            return res.pkupdate(
                path=simulation_db.user_path(uid=uid, check=True).join(
                    res.sim_type,
                    res.sid_or_lib,
                    res.basename,
                ),
            )
        except Exception as e:
            pkdlog(
                "error={} uid={} sim_type={} sid_or_lib={} basename={}",
                e,
                uid,
                sim_type,
                sid_or_lib,
                basename,
            )
            return None

    if len(uri) <= 0:
        # no point in logging anything
        return None
    if is_arg_uri:
        p = uri.split("/")
    else:
        m = _URI_RE.search(uri)
        if not m:
            pkdlog("uri={} missing prefix={}", uri, sirepo.job.SIM_DB_FILE_URI)
            return None
        p = m.group(1).split("/")
        if p[0] != uid:
            pkdlog("uri={} does not match expect_uid={}", p[0], uid)
            return None
        p.pop(0)
    if len(p) != 3:
        pkdlog("uri={} invalid part count is_arg_uri={}", uri, is_arg_uri)
        return None
    return _result(*p)


_cfg = pkconfig.init(
    server_token=(None, str, "credential to connect"),
    server_uri=(None, str, "how to connect to server"),
)
