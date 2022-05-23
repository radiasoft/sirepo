"""Manage user sessions"""

from pykern.pkdebug import pkdp
import contextlib
import flask
import sirepo.auth
import sirepo.auth_db
import sirepo.srtime
import sirepo.util
import sqlalchemy

_Session = None

@contextlib.contextmanager
def session():
    # get agent id header
    # if no header, create row
    # else assert header is in db
    # update request time
    # send begin session if N time has elapsed between previous request time
    i = flask.request.headers.get('X-Sirepo-UserAgentId')
    pkdp('X-Sirepo-UserAgentId={}', i)

    if not i:
        #TODO(rorour) make is_logged_in public
        l = sirepo.auth._is_logged_in()
        t = sirepo.srtime.utc_now()
        _Session(
            #TODO(rorour) get 8 from const
            user_agent_id=sirepo.util.random_base62(8),
            login_state=l,
            uid=sirepo.auth.logged_in_user() if l else None,
            start_time=t,
            request_time=t,
        ).save()
    yield


def _init_model(base):
    global _Session
    class _Session(base):
        __tablename__ = 'session_t'
        user_agent_id = sqlalchemy.Column(base.STRING_ID, unique=True, primary_key=True)
        login_state = sqlalchemy.Column(sqlalchemy.Boolean(), nullable=False)
        uid = sqlalchemy.Column(base.STRING_ID, unique=True)
        start_time = sqlalchemy.Column(sqlalchemy.DateTime(), nullable=False)
        request_time = sqlalchemy.Column(sqlalchemy.DateTime(), nullable=False)
        # TODO(rorour) enable when using websockets
        # end_time = sqlalchemy.Column(sqlalchemy.DateTime(), nullable=False)


sirepo.auth_db.init_model(_init_model)