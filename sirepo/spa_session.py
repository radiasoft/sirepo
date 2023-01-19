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

_RENEW_SESSION_TIMEOUT_SECS = 5 * 60

_USER_AGENT_ID_HEADER = "X-Sirepo-UserAgentId"

_ID_ATTR = "session_id"

_DB = PKDict()

_initialized = None


def init_module():
    global _initialized, _cfg
    if _initialized:
        return
    _initialized = True
    # sirepo.events.register(PKDict(end_api_call=_end_api_call))


def init_quest(qcall):
    def _begin():
        try:
            qcall.call_api("beginSession")
        except Exception as e:
            pkdlog("error={} trying api_beginSession stack={}", e, pkdexc())

    def _new_session(user_agent_id=None):
        if not qcall.auth.is_logged_in():
            return
        with sirepo.util.THREAD_LOCK:
            _DB[qcall.auth.logged_in_user(check_path=False)] = sirepo.srtime.utc_now()
        _begin()

    def _update_session():
        s = _DB.get(qcall.auth.logged_in_user(check_path=False))
        if s:
            t = sirepo.srtime.utc_now()
            if (
                t - s.request_time
                > datetime.timedelta(seconds=_RENEW_SESSION_TIMEOUT_SECS)
            ):
                _begin()
        # don't need THREAD_LOCK here, because these values are likely to be constant
        s.request_time =
        return user_agent_id

    if qcall.sreq.method_is_post() or not qcall.auth.is_logged_in():
        _update_session()

def _end_api_call(qcall, kwargs):
    i = qcall.bucket_unchecked_get(_ID_ATTR)
    if i:
        kwargs.resp.header_set(_USER_AGENT_ID_HEADER, i)
