# -*- coding: utf-8 -*-
"""Manage user sessions

:copyright: Copyright (c) 2022 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkdebug import pkdp, pkdlog, pkdexc
from pykern.pkcollections import PKDict
import contextlib
import datetime
import sirepo.auth_db
import sirepo.events
import sirepo.quest
import sirepo.srtime
import sirepo.util
import sqlalchemy

_RENEW_SESSION_TIMEOUT_SECS = 5 * 60

_USER_AGENT_ID_HEADER = "X-Sirepo-UserAgentId"

_ID_ATTR = "session_id"

_initialized = None


def init_module():
    global _initialized
    if _initialized:
        return
    _initialized = True
    sirepo.events.register(PKDict(end_api_call=_end_api_call))


def init_quest(qcall):
    def _new_session():
        l = qcall.auth.is_logged_in()
        t = sirepo.srtime.utc_now()
        i = sirepo.util.random_base62()
        sirepo.auth_db.SPASession(
            user_agent_id=i,
            login_state=l,
            uid=qcall.auth.logged_in_user(check_path=False) if l else None,
            start_time=t,
            request_time=t,
        ).save()
        if l:
            _begin()
        return i

    def _update_session(user_agent_id):
        s = sirepo.auth_db.SPASession.search_by(user_agent_id=user_agent_id)
        if not s:
            pkdlog("Restarting session for user_agent_id={}", user_agent_id)
            return _new_session()
        l = qcall.auth.is_logged_in()
        t = s.request_time
        if (
            sirepo.srtime.utc_now() - t
            > datetime.timedelta(seconds=_RENEW_SESSION_TIMEOUT_SECS)
            and l
        ):
            _begin()
        s.login_state = l
        s.request_time = sirepo.srtime.utc_now()
        s.save()
        return i

    def _begin():
        try:
            qcall.call_api("beginSession")
        except Exception as e:
            pkdlog("error={} trying api_beginSession stack={}", e, pkdexc())

    i = qcall.sreq.header_uget(_USER_AGENT_ID_HEADER)
    if qcall.sreq.method_is_post():
        i = _update_session(i) if i else _new_session()
    qcall.bucket_set(_ID_ATTR, i)


def _end_api_call(qcall, kwargs):
    kwargs.resp.headers[_USER_AGENT_ID_HEADER] = qcall.bucket_uget(_ID_ATTR)
