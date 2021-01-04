# -*- coding: utf-8 -*-
"""Getting and putting simulation db files

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkio
from pykern.pkdebug import pkdp
from pykern.pkcollections import PKDict
import functools
import sirepo.job
import sirepo.simulation_db
import sirepo.tornado
import tornado.web

# TODO(e-carlin): rename key to token
_TOKEN_TO_UID = PKDict()



class FileReq(tornado.web.RequestHandler):
    SUPPORTED_METHODS = ['GET','PUT']

    def get(self, path):
        self.__validate_req()
        p = sirepo.srdb.root().join(path)
        if not p.exists():
            raise sirepo.tornado.error_not_found()
        self.write(pkio.read_binary(p))

    def put(self, path):
        self.__validate_req()
        sirepo.srdb.root().join(path).write_binary(self.request.body)

    def __validate_req(self):
        t = self.request.headers.get(sirepo.job.AUTH_HEADER)
        if not t:
            raise sirepo.tornado.error_forbidden()
        p = t.split(' ')
        if len(p) != 2:
            raise sirepo.tornado.error_forbidden()
        if p[0] != sirepo.job.AUTH_HEADER_SCHEME_BEARER \
            or not sirepo.job.UNIQUE_KEY_RE.search(p[1]):
            raise sirepo.tornado.error_forbidden()
        if p[1] not in _TOKEN_TO_UID:
            raise sirepo.tornado.error_forbidden()
        sirepo.simulation_db.validate_path(
            self.request.path.split('/')[2:],
            _TOKEN_TO_UID[p[1]],
        )


def get_token(uid):
    for u, k in _TOKEN_TO_UID.items():
        if u == uid:
            return k
    k = sirepo.job.unique_key()
    _TOKEN_TO_UID[k] = uid
    return k
