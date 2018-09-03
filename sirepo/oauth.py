# -*- coding: utf-8 -*-
u"""OAUTH support

:copyright: Copyright (c) 2016 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function

from flask_sqlalchemy import SQLAlchemy
from pykern import pkconfig, pkcollections
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp
from sirepo import cookie
from sirepo import server
from sirepo import simulation_db
from sirepo import api_perm
from sirepo import api_auth
from sirepo import uri_router
from sirepo import util
import flask
import flask.sessions
import flask_oauthlib.client
import os.path
import sqlalchemy
import threading


# oauth_login_state values
_ANONYMOUS = 'a'
_LOGGED_IN = 'li'
_LOGGED_OUT = 'lo'

_ANONYMOUS_OAUTH_TYPE = 'anonymous'
_LOGIN_STATE_MAP = {
    _ANONYMOUS: _ANONYMOUS_OAUTH_TYPE,
    _LOGGED_IN: 'logged_in',
    _LOGGED_OUT: 'logged_out',
}

_USER_DB_FILE = 'user.db'

# cookie keys for oauth
_COOKIE_NAME = 'sron'
_COOKIE_NEXT = 'sronx'
_COOKIE_NONCE = 'sronn'
_COOKIE_STATE = 'sros'

_db = None

#: Locking of _db calls
_db_serial_lock = threading.RLock()


def all_uids(app):
#TODO(robnagler) do we need locking
    res = set()
    for u in User.query.all():
        res.add(u.uid)
    return res


def allow_cookieless_user():
    set_default_state(logged_out_as_anonymous=True)


@api_perm.allow_login
def api_oauthAuthorized(oauth_type):
    return authorized_callback(oauth_type)


@api_perm.allow_cookieless_user
def api_oauthLogin(simulation_type, oauth_type):
    return authorize(simulation_type, oauth_type)


@api_perm.allow_visitor
def api_oauthLogout(simulation_type):
    return logout(simulation_type)


def authorize(simulation_type, oauth_type):
    """Redirects to an OAUTH request for the specified oauth_type ('github').

    If oauth_type is 'anonymous', the current session is cleared.
    """
    oauth_next = '/{}#{}'.format(simulation_type, flask.request.args.get('next', ''))
    if oauth_type == _ANONYMOUS_OAUTH_TYPE:
        _update_session(_ANONYMOUS)
        return server.javascript_redirect(oauth_next)
    state = util.random_base62()
    cookie.set_value(_COOKIE_NONCE, state)
    cookie.set_value(_COOKIE_NEXT, oauth_next)
    callback = cfg.github_callback_uri
    if not callback:
        from sirepo import uri_router
        callback = uri_router.uri_for_api(
            'oauthAuthorized',
            dict(oauth_type=oauth_type),
        )
    return _oauth_client(oauth_type).authorize(
        callback=callback,
        state=state,
    )


def authorized_callback(oauth_type):
    """Handle a callback from a successful OAUTH request. Tracks oauth
    users in a database.
    """
    oc = _oauth_client(oauth_type)
    resp = oc.authorized_response()
    if not resp:
        util.raise_forbidden('missing oauth response')
    state = _remove_cookie_key(_COOKIE_NONCE)
    if state != flask.request.args.get('state', ''):
        util.raise_forbidden(
            'mismatch oauth state: {} != {}',
            state,
            flask.request.args.get('state'),
        )
    # fields: id, login, name
    user_data = oauth.get('user', token=(resp['access_token'], '')).data
    user = _update_database(user_data, oauth_type)
    _update_session(_LOGGED_IN, user.user_name)
    return server.javascript_redirect(_remove_cookie_key(_COOKIE_NEXT))


def logout(simulation_type):
    """Sets the login_state to logged_out and clears the user session.
    """
    _update_session(_LOGGED_OUT)
    return flask.redirect('/{}'.format(simulation_type))


def init_apis(app):
    _init(app)
    _init_user_model()
    _init_tables(app)
    uri_router.register_api_module()
    api_auth.register_login_module()
    _init_beaker_compat()


def set_default_state(logged_out_as_anonymous=False):
    if not cookie.has_key(_COOKIE_STATE):
        _update_session(_ANONYMOUS)
    elif logged_out_as_anonymous and cookie.get_value(_COOKIE_STATE) == _LOGGED_OUT:
        _update_session(_ANONYMOUS)
    return pkcollections.Dict(
        login_state=_LOGIN_STATE_MAP.get(cookie.get_value(_COOKIE_STATE), _ANONYMOUS_OAUTH_TYPE),
        user_name=cookie.get_value(_COOKIE_NAME),
    )


class _FlaskSession(dict, flask.sessions.SessionMixin):
    pass


class _FlaskSessionInterface(flask.sessions.SessionInterface):
    """Emphemeral session for oauthlib.client state

    Without this class, Flask creates a NullSession which can't
    be written to. Flask assumes the session needs to be persisted
    to cookie or a db, which isn't true in our case.
    """
    def open_session(*args, **kwargs):
        return _FlaskSession()

    def save_session(*args, **kwargs):
        pass


def _beaker_compat_map_keys(key_map):
    key_map['key']['oauth_login_state'] = _COOKIE_STATE
    key_map['key']['oauth_user_name'] = _COOKIE_NAME
    # reverse map of login state values
    key_map['value'] = dict(map(lambda k: (_LOGIN_STATE_MAP[k], k), _LOGIN_STATE_MAP))


def _db_filename(app):
    return str(app.sirepo_db_dir.join(_USER_DB_FILE))


def _init(app):
    global _db

    app.session_interface = _FlaskSessionInterface()
    app.config.update(
        SQLALCHEMY_DATABASE_URI='sqlite:///{}'.format(_db_filename(app)),
        SQLALCHEMY_COMMIT_ON_TEARDOWN=True,
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )
    _db = SQLAlchemy(app, session_options=dict(autoflush=True))
    global cfg
    cfg = pkconfig.init(
        github_key=(None, str, 'GitHub application key'),
        github_secret=(None, str, 'GitHub application secret'),
        github_callback_uri=(None, str, 'GitHub application callback URI'),
    )
    if not cfg.github_key or not cfg.github_secret:
        raise RuntimeError('Missing GitHub oauth config')



def _init_beaker_compat():
    from sirepo import beaker_compat
    beaker_compat.oauth_hook = _beaker_compat_map_keys



def _init_tables(app):
    """Creates sql lite tables"""
    if not os.path.exists(_db_filename(app)):
        pkdlog('creating user oauth database')
        _db.create_all()


def _init_user_model():
    """Creates User class bound to dynamic `_db` variable"""
    global User

    class User(_db.Model):
        __tablename__ = 'user_t'
        uid = _db.Column(_db.String(8), primary_key=True)
        user_name = _db.Column(_db.String(100), nullable=False)
        display_name = _db.Column(_db.String(100))
        oauth_type = _db.Column(
            _db.Enum('github', 'test', name='oauth_type'),
            nullable=False
        )
        oauth_id = _db.Column(_db.String(100), nullable=False)
        __table_args__ = (sqlalchemy.UniqueConstraint('oauth_type', 'oauth_id'),)

        def __init__(self, uid, user_name, display_name, oauth_type, oauth_id):
            self.uid = uid
            self.user_name = user_name
            self.display_name = display_name
            self.oauth_type = oauth_type
            self.oauth_id = oauth_id


def _oauth_client(oauth_type):
    if oauth_type == 'github':
        return flask_oauthlib.client.OAuth(flask.current_app).remote_app(
            'github',
            consumer_key=cfg.github_key,
            consumer_secret=cfg.github_secret,
            base_url='https://api.github.com/',
            request_token_url=None,
            access_token_method='POST',
            access_token_url='https://github.com/login/oauth/access_token',
            authorize_url='https://github.com/login/oauth/authorize',
        )
    raise RuntimeError('Unknown oauth_type: {}'.format(oauth_type))


def _remove_cookie_key(name):
    value = cookie.get_value(name)
    cookie.unchecked_remove(name)
    return value


def _update_database(user_data, oauth_type):
    with _db_serial_lock:
        user = User.query.filter_by(oauth_id=user_data['id'], oauth_type=oauth_type).first()
        session_uid = cookie.get_user(checked=False)
        if user:
            if session_uid and session_uid != user.uid:
                simulation_db.move_user_simulations(user.uid)
            user.user_name = user_data['login']
            user.display_name = user_data['name']
            cookie.set_user(user.uid)
        else:
            if not session_uid:
                # ensures the user session (uid) is ready if new user logs in from logged-out session
                pkdlog('creating new session for user: {}', user_data['id'])
                simulation_db.simulation_dir('')
            user = User(cookie.get_user(), user_data['login'], user_data['name'], oauth_type, user_data['id'])
        _db.session.add(user)
        _db.session.commit()
        return user

def _update_session(login_state, user_name=''):
    cookie.set_value(_COOKIE_STATE, login_state)
    cookie.set_value(_COOKIE_NAME, user_name)
