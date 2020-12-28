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
import sirepo.tornado
import tornado.web

_KEY_TO_UID = PKDict()


# Must be defined before use
def _sim_db_file_req_validated(func):
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        t = self.request.headers.get(sirepo.job.AUTH_HEADER)
        if not t:
            sirepo.tornado.raise_unauthorized()
        p = t.split(' ')
        if len(p) != 2:
            sirepo.tornado.raise_unauthorized()
        if p[0] != sirepo.job.AUTH_HEADER_SCHEME_BEARER \
           or not sirepo.job.UNIQUE_KEY_RE.search(p[1]):
            sirepo.tornado.raise_unauthorized()
        if p[1] not in _KEY_TO_UID or \
           self.request.path.split('/')[3] != _KEY_TO_UID[p[1]]:
            sirepo.tornado.raise_forbidden()
        # TODO(e-carlin): discuss with rn what validation needs to happen
        p = self.request.path
        if p.count('.') > 1:
            sirepo.tornado.raise_not_found()
        return func(self, *args, **kwargs)
    return wrapper


class FileReq(tornado.web.RequestHandler):
    SUPPORTED_METHODS = ['GET','PUT']

    @_sim_db_file_req_validated
    def get(self, path):
        p = sirepo.srdb.root().join(path)
        if not p.exists():
            sirepo.tornado.raise_not_found()
        self.write(pkio.read_binary(p))

    @_sim_db_file_req_validated
    def put(self, path):
        sirepo.srdb.root().join(path).write_binary(self.request.body)


def get_key(uid):
    for u, k in _KEY_TO_UID.items():
        if u == uid:
            return k
    k = sirepo.job.unique_key()
    _KEY_TO_UID[k] = uid
    return k
