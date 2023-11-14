# -*- coding: utf-8 -*-
"""Getting and putting simulation db files

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern import pkio
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdlog
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

    def __authenticated_path(self):
        u = self._rs_authenticate()
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
