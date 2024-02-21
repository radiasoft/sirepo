# -*- coding: utf-8 -*-
"""Manage user sessions

:copyright: Copyright (c) 2022 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkdebug import pkdp, pkdlog, pkdexc
from pykern.pkcollections import PKDict
import contextlib
import datetime
import sirepo.quest
import sirepo.srtime
import sirepo.util
import threading

_REFRESH_SESSION = datetime.timedelta(seconds=5 * 60)

_DB = PKDict()

_initialized = None


def init_module():
    global _initialized, _cfg
    if _initialized:
        return
    _initialized = True


async def maybe_begin(qcall):
    async def _begin():
        try:
            (await qcall.call_api("beginSession", body=PKDict())).destroy()
        except Exception as e:
            pkdlog("ignoring exception={} stack={}", e, pkdexc())

    def _check():
        try:
            u = qcall.auth.logged_in_user(check_path=True)
        except sirepo.util.UserDirNotFound as e:
            pkdlog("ignoring exception={}, because api call will check", e)
            return False
        t = sirepo.srtime.utc_now()
        s = _DB.get(u)
        if s:
            if t - s.request_time < _REFRESH_SESSION:
                return False
            s.request_time = t
        else:
            s = PKDict(request_time=t)
            _DB[u] = s
        return True

    if qcall.sreq.method_is_post() and qcall.auth.is_logged_in() and _check():
        await _begin()
