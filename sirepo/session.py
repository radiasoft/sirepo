"""Manage user sessions"""

from pykern.pkdebug import pkdp, pkdlog, pkdexc
from pykern.pkcollections import PKDict
import contextlib
import datetime
import sirepo.quest
import sirepo.auth_db
import sirepo.events
import sirepo.srtime
import sirepo.util
import sqlalchemy

_RENEW_SESSION_TIMEOUT_SECS = 5 * 60

_Session = None

_USER_AGENT_ID_HEADER = "X-Sirepo-UserAgentId"

_ID_ATTR = "session_id"

_initialized = None


def init_module():
    global _initialized
    if _initialized:
        return
    _initialized = True
    sirepo.auth_db.init_model(_init_model)
    sirepo.events.register(PKDict(end_api_call=_end_api_call))


def quest_init(qcall):
    def _new_session():
        l = qcall.auth.is_logged_in()
        t = sirepo.srtime.utc_now()
        i = sirepo.util.random_base62()
        _Session(
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
        s = _Session.search_by(user_agent_id=user_agent_id)
        assert s, f"No session for user_agent_id={user_agent_id}"
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

    def _begin():
        try:
            qcall.call_api("beginSession")
        except Exception as e:
            pkdlog("error={} trying api_beginSession stack={}", e, pkdexc())

    i = qcall.sreq.header_uget(_USER_AGENT_ID_HEADER)
    if qcall.sreq.method_is_post():
        if not i:
            i = _new_session()
        else:
            _update_session(i)
    qcall.bucket_set(_ID_ATTR, i)


def _end_api_call(qcall, kwargs):
    kwargs.resp.headers[_USER_AGENT_ID_HEADER] = qcall.bucket_uget(_ID_ATTR)


def _init_model(base):
    global _Session

    class _Session(base):
        __tablename__ = "session_t"
        user_agent_id = sqlalchemy.Column(base.STRING_ID, unique=True, primary_key=True)
        login_state = sqlalchemy.Column(sqlalchemy.Boolean(), nullable=False)
        uid = sqlalchemy.Column(base.STRING_ID)
        start_time = sqlalchemy.Column(sqlalchemy.DateTime(), nullable=False)
        request_time = sqlalchemy.Column(sqlalchemy.DateTime(), nullable=False)
        # TODO(rorour) enable when using websockets
        # end_time = sqlalchemy.Column(sqlalchemy.DateTime(), nullable=False)
