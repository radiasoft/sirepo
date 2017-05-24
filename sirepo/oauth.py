# -*- coding: utf-8 -*-
u"""OAUTH support

:copyright: Copyright (c) 2016 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function

from flask_sqlalchemy import SQLAlchemy
from pykern import pkconfig, pkcollections
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp
from sirepo import server
from sirepo import simulation_db
import flask
import flask_oauthlib.client
import os.path
import sqlalchemy
import threading
import werkzeug.exceptions
import werkzeug.security

# flask session oauth_login_state values
_ANONYMOUS = 'anonymous'
_LOGGED_IN = 'logged_in'
_LOGGED_OUT = 'logged_out'

_USER_DB_FILE = 'user.db'

_db = None

#: Locking of _db calls
_db_serial_lock = threading.RLock()


def all_uids(app):
    res = set()
    for u in User.query.all():
        res.add(u.uid)
    return res


def authorize(simulation_type, app, oauth_type):
    """Redirects to an OAUTH request for the specified oauth_type ('github').

    If oauth_type is 'anonymous', the current session is cleared.
    """
    oauth_next = '/{}#{}'.format(simulation_type, flask.request.args.get('next') or '')
    if oauth_type == _ANONYMOUS:
        _update_session(_ANONYMOUS)
        server.clear_session_user()
        return server.javascript_redirect(oauth_next)
    state = werkzeug.security.gen_salt(64)
    flask.session['oauth_nonce'] = state
    flask.session['oauth_next'] = oauth_next
    callback = cfg.github_callback_uri
    if not callback:
        from sirepo import uri_router
        callback = uri_router.uri_for_api(
            'oauthAuthorized',
            dict(oauth_type=oauth_type),
        )
    return _oauth_client(app, oauth_type).authorize(
        callback=callback,
        state=state,
    )


def authorized_callback(app, oauth_type):
    """Handle a callback from a successful OAUTH request. Tracks oauth
    users in a database.
    """
    oauth = _oauth_client(app, oauth_type)
    resp = oauth.authorized_response()
    if not resp:
        pkdlog('missing oauth response')
        werkzeug.exceptions.abort(403)
    state = _remove_session_key('oauth_nonce')
    if state != flask.request.args.get('state'):
        pkdlog('mismatch oauth state: {} != {}', state, flask.request.args.get('state'))
        werkzeug.exceptions.abort(403)
    # fields: id, login, name
    user_data = oauth.get('user', token=(resp['access_token'], '')).data
    user = _update_database(user_data, oauth_type)
    _update_session(_LOGGED_IN, user.user_name)
    return server.javascript_redirect(_remove_session_key('oauth_next'))


def logout(simulation_type):
    """Sets the login_state to logged_out and clears the user session.
    """
    _update_session(_LOGGED_OUT)
    server.clear_session_user()
    return flask.redirect('/{}'.format(simulation_type))


def set_default_state(logged_out_as_anonymous=False):
    if 'oauth_login_state' not in flask.session:
        _update_session(_ANONYMOUS)
    elif logged_out_as_anonymous and flask.session['oauth_login_state'] == _LOGGED_OUT:
        _update_session(_ANONYMOUS)
    return pkcollections.Dict(
        login_state=flask.session['oauth_login_state'],
        user_name=flask.session['oauth_user_name'],
    )


def _db_filename(app):
    return str(app.sirepo_db_dir.join(_USER_DB_FILE))


def _init(app):
    global _db
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


def _init_tables(app):
    if not os.path.exists(_db_filename(app)):
        pkdlog('creating user oauth database')
        _db.create_all()


def _oauth_client(app, oauth_type):
    if oauth_type == 'github':
        return flask_oauthlib.client.OAuth(app).remote_app(
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


def _remove_session_key(name):
    value = flask.session[name]
    del flask.session[name]
    return value


def _update_database(user_data, oauth_type):
    with _db_serial_lock:
        user = User.query.filter_by(oauth_id=user_data['id'], oauth_type=oauth_type).first()
        session_uid = server.session_user(checked=False)
        if user:
            if session_uid and session_uid != user.uid:
                simulation_db.move_user_simulations(user.uid)
            user.user_name = user_data['login']
            user.display_name = user_data['name']
            server.session_user(user.uid)
        else:
            if not session_uid:
                # ensures the user session (uid) is ready if new user logs in from logged-out session
                pkdlog('creating new session for user: {}', user_data['id'])
                simulation_db.simulation_dir('')
            user = User(server.session_user(), user_data['login'], user_data['name'], oauth_type, user_data['id'])
        _db.session.add(user)
        _db.session.commit()
        return user

def _update_session(login_state, user_name=''):
    flask.session['oauth_login_state'] = login_state
    flask.session['oauth_user_name'] = user_name


_init(server.app)


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


_init_tables(server.app)
