"""Manage user sessions"""

from pykern.pkdebug import pkdp
from pykern.pkcollections import PKDict
import contextlib
import datetime
import flask
import sirepo.auth
import sirepo.auth_db
import sirepo.events
import sirepo.request
import sirepo.srcontext
import sirepo.srtime
import sirepo.uri_router  #TODO(rorour) remove
import sirepo.util
import sqlalchemy

_SRCONTEXT_KEY = __name__

_Session = None


def _event_end_api_call(kwargs):
    kwargs.resp.headers['X-Sirepo-UserAgentId'] = sirepo.srcontext.get(_SRCONTEXT_KEY)


@contextlib.contextmanager
def session():
    # get agent id header
    # if no header, create row
    # else assert header is in db
    # update request time
    # send begin session if N time has elapsed between previous request time
    i = flask.request.headers.get('X-Sirepo-UserAgentId')
    pkdp('X-Sirepo-UserAgentId={}', i)
    pkdp('path={}', flask.request.path)
    #TODO(rorour) make self.request_method which uses flask request method
    if flask.request.method != 'POST' or 'static' in flask.request.path or 'schema' in flask.request.path:
        yield
        return
    if not i:
        l = sirepo.auth.is_logged_in()
        t = sirepo.srtime.utc_now()
        #TODO(rorour) get 8 from const
        i = sirepo.util.random_base62(8)
        _Session(
            user_agent_id=i,
            login_state=l,
            uid=sirepo.auth.logged_in_user() if l else None,
            start_time=t,
            request_time=t,
        ).save()
        # TODO(rorour) call self.call_api correctly
        sirepo.uri_router.call_api('wakeAgent', data=PKDict(simulationType='srw'))
    else:
        s = _Session.search_by(user_agent_id=i)
        assert s, f'No session for user_agent_id={i}'
        t = s.request_time
        if sirepo.srtime.utc_now() - t > datetime.timedelta(minutes=1):  # TODO(rorour) use constant tune 60
            sirepo.uri_router.call_api('wakeAgent', data=PKDict(simulationType='srw'))
        s.request_time = sirepo.srtime.utc_now()
        s.save()
    sirepo.srcontext.set(_SRCONTEXT_KEY, i)
    yield


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
