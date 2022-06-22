"""Manage user sessions"""

from pykern.pkdebug import pkdp
from pykern.pkcollections import PKDict
import contextlib
import datetime
import sirepo.api
import sirepo.auth
import sirepo.auth_db
import sirepo.events
import sirepo.srcontext
import sirepo.srtime
import sirepo.uri_router  #TODO(rorour) remove
import sirepo.util
import sqlalchemy

_RENEW_SESSION_TIMEOUT_SECS = 5 * 60

_SRCONTEXT_KEY = __name__

_USER_AGENT_ID_LEN = 8

_Session = None


def _event_end_api_call(kwargs):
    i = sirepo.srcontext.get(_SRCONTEXT_KEY)
    if i:
        kwargs.resp.headers['X-Sirepo-UserAgentId'] = i


@contextlib.contextmanager
def begin(sreq):
    def _new_session():
        l = sirepo.auth.is_logged_in()
        t = sirepo.srtime.utc_now()
        _Session(
            user_agent_id=sirepo.util.random_base62(_USER_AGENT_ID_LEN),
            login_state=l,
            uid=sirepo.auth.logged_in_user() if l else None,
            start_time=t,
            request_time=t,
        ).save()
        _begin()

    def _update_session(user_agent_id):
        s = _Session.search_by(user_agent_id=user_agent_id)
        assert s, f'No session for user_agent_id={user_agent_id}'
        t = s.request_time
        if sirepo.srtime.utc_now() - t > datetime.timedelta(seconds=_RENEW_SESSION_TIMEOUT_SECS):
            _begin()
        s.request_time = sirepo.srtime.utc_now()
        s.save()

    i = sreq.headers().get('X-Sirepo-UserAgentId')
    if not sreq.has_params():
        yield
        return
    if not i:
        _new_session()
    else:
        _update_session(i)
    sirepo.srcontext.set(_SRCONTEXT_KEY, i)
    yield


def _begin():
    from sirepo import job_api
    job_api.begin_session()

def _init():
    sirepo.events.register(PKDict(
        end_api_call=_event_end_api_call
    ))
    sirepo.auth_db.init_model(_init_model)


def _init_model(base):
    global _Session
    class _Session(base):
        __tablename__ = 'session_t'
        user_agent_id = sqlalchemy.Column(base.STRING_ID, unique=True, primary_key=True)
        login_state = sqlalchemy.Column(sqlalchemy.Boolean(), nullable=False)
        uid = sqlalchemy.Column(base.STRING_ID)
        start_time = sqlalchemy.Column(sqlalchemy.DateTime(), nullable=False)
        request_time = sqlalchemy.Column(sqlalchemy.DateTime(), nullable=False)
        # TODO(rorour) enable when using websockets
        # end_time = sqlalchemy.Column(sqlalchemy.DateTime(), nullable=False)


_init()
