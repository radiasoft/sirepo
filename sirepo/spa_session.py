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
    _cfg = pykern.pkconfig.init(
        use_auth_db=(False, bool, "use auth_db otherwise use thread locked values"),
    )
    sirepo.events.register(PKDict(end_api_call=_end_api_call))


def init_quest(qcall):
    def _begin():
        try:
            qcall.call_api("beginSession")
        except Exception as e:
            pkdlog("error={} trying api_beginSession stack={}", e, pkdexc())

    def _new_session(user_agent_id=None):
        l = qcall.auth.is_logged_in()
        t = sirepo.srtime.utc_now()
        if user_agent_id is None:
            user_agent_id = sirepo.util.random_base62()
        k = PKDict(
            login_state=l,
            request_time=t,
            start_time=t,
            uid=qcall.auth.logged_in_user(check_path=False) if l else None,
            user_agent_id=user_agent_id,
        )
        if _cfg.use_auth_db:
            qcall.auth_db.model("SPASession", **k).save()
        else:
            with sirepo.util.THREAD_LOCK:
                _DB[user_agent_id] = k
        if l:
            _begin()
        return user_agent_id

    def _update_session(user_agent_id):
        if _cfg.use_auth_db:
            s = qcall.auth_db.model("SPASession").unchecked_search_by(
                user_agent_id=user_agent_id
            )
        else:
            s = _DB.get(user_agent_id)
        if not s:
            pkdlog("Restarting session for user_agent_id={}", user_agent_id)
            return _new_session(user_agent_id=user_agent_id)
        l = qcall.auth.is_logged_in()
        t = s.request_time
        if (
            sirepo.srtime.utc_now() - t
            > datetime.timedelta(seconds=_RENEW_SESSION_TIMEOUT_SECS)
            and l
        ):
            _begin()
        # don't need THREAD_LOCK here, because these values are likely to be constant
        if s.login_state != l:
            s.login_state = l
            if l:
                # Only update the user if logged in, otherwise keep uid for the record
                s.uid = qcall.auth.logged_in_user(check_path=False)
        s.request_time = sirepo.srtime.utc_now()
        if _cfg.use_auth_db:
            s.save()
        return user_agent_id

    i = qcall.sreq.header_uget(_USER_AGENT_ID_HEADER)
    if qcall.sreq.method_is_post():
        i = _update_session(i) if i else _new_session()
    qcall.bucket_set(_ID_ATTR, i)
    if _cfg.use_auth_db:
        # TODO(robnagler): commit here is necessary because we want to log all
        # accesses
        qcall.auth_db.commit()


def _end_api_call(qcall, kwargs):
    kwargs.resp.header_set(_USER_AGENT_ID_HEADER, qcall.bucket_unchecked_get(_ID_ATTR))
