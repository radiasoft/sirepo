# -*- coding: utf-8 -*-
"""Manage user sessions

:copyright: Copyright (c) 2022 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkdebug import pkdp, pkdlog, pkdexc
from pykern.pkcollections import PKDict
import contextlib
import datetime
import pykern.pkconfig
import sirepo.events
import sirepo.quest
import sirepo.srtime
import sirepo.util
import sqlalchemy

_REFRESH_SESSION = datetime.timedelta(seconds=5 * 60)

_DB = PKDict()

_initialized = None


def init_module():
    global _initialized, _cfg
    if _initialized:
        return
    _initialized = True


def init_quest(qcall):
    def _begin():
        try:
            qcall.call_api("beginSession").destroy()
        except Exception as e:
            pkdlog("error={} trying api_beginSession stack={}", e, pkdexc())

    def _check():
        u = qcall.auth.logged_in_user(check_path=False)
        t = sirepo.srtime.utc_now()
        s = _DB.get(u)
        if s:
            if t - s.request_time < _REFRESH_SESSION:
                return False
            with sirepo.util.THREAD_LOCK:
                s.request_time = t
        else:
            s = PKDict(request_time=t)
            with sirepo.util.THREAD_LOCK:
                _DB[u] = s
        return True

    if qcall.sreq.method_is_post() and qcall.auth.is_logged_in() and _check():
        _begin()
