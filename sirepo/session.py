"""Manage user sessions"""

from pykern.pkdebug import pkdp, pkdlog, pkdexc
from pykern.pkcollections import PKDict
import contextlib
import datetime
import sirepo.quest
import sirepo.auth
import sirepo.auth_db
import sirepo.events
import sirepo.srtime
import sirepo.util
import sqlalchemy

_RENEW_SESSION_TIMEOUT_SECS = 5 * 60

_Session = None

_USER_AGENT_ID_HEADER = "X-Sirepo-UserAgentId"


def qcall_init(qcall):
    def _new_session():
        l = sirepo.auth.is_logged_in(sreq)
        t = sirepo.srtime.utc_now()
        i = sirepo.util.random_base62()
        _Session(
            user_agent_id=i,
            login_state=l,
            uid=sirepo.auth.logged_in_user(sreq, check_path=False) if l else None,
            start_time=t,
            request_time=t,
        ).save()
        if l:
            _begin()
        return i

    def _update_session(user_agent_id):
        s = _Session.search_by(user_agent_id=user_agent_id)
        assert s, f"No session for user_agent_id={user_agent_id}"
        l = sirepo.auth.is_logged_in(sreq)
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

    i = sreq.http_header(_USER_AGENT_ID_HEADER)
    if sreq.http_method_is_post():
        if not i:
            i = _new_session()
        else:
            _update_session(i)
    qcall.qcall_object("session", QCallObject(i))


class QCallObject(sirepo.quest.QCallObject):
    def __init__(self, session_id):
        super().__init__(_id=session_id)

    def quest_result_handler(self, qres):
        if self._id:
            qres.headers[_USER_AGENT_ID_HEADER] = self._id


def init():
    sirepo.auth_db.init_model(_init_model)


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
