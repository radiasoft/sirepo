# -*- coding: utf-8 -*-
u"""OAUTH support

:copyright: Copyright (c) 2016 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function

from pykern import pkconfig, pkcollections
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp
from sirepo import api_perm
from sirepo import cookie
from sirepo import server
from sirepo import uri_router
from sirepo import user_db
from sirepo import user_state
from sirepo import util
import sirepo.template
import flask
import flask.sessions
import flask_oauthlib.client
import sqlalchemy


#: GitHub/OAuth allows anonymous users
ALLOW_ANONYMOUS_SESSION = True

#: How do we authenticate
AUTH_METHOD = 'github'

#: oauth_type value that should be passed in always
DEFAULT_OAUTH_TYPE = AUTH_METHOD

#: Used by user_db
UserModel = None

# cookie keys for oauth
_COOKIE_NEXT = 'sronx'
_COOKIE_NONCE = 'sronn'


@api_perm.require_cookie_sentinel
def api_oauthAuthorized(oauth_type):
    """Handle a callback from a successful OAUTH request.

    Tracks oauth users in a database.
    """
    with user_db.thread_lock:
        oc = _oauth_client(oauth_type)
        resp = oc.authorized_response()
        if not resp:
            util.raise_forbidden('missing oauth response')
        expect = cookie.unchecked_remove(_COOKIE_NONCE)
        got = flask.request.args.get('state', '')
        if expect != got:
            util.raise_forbidden(
                'mismatch oauth state: expected {} != got {}',
                expect,
                got,
            )
        data = oc.get('user', token=(resp['access_token'], '')).data
        u = UserModel.search_by(oauth_id=data['id'], oauth_type=oauth_type)
        if u:
            u.display_name = data['name']
            u.user_name = data['login']
        else:
            if not cookie.has_user_value():
                from sirepo import simulation_db
                simulation_db.user_create()
            # first time logging in to oauth so create oauth record
            u = User(
                display_name=data['name'],
                oauth_id=data['id'],
                oauth_type=oauth_type,
                uid=cookie.get_user(),
                user_name=data['login'],
            )
        u.save()
        user_state.login_as_user(u)
    return server.javascript_redirect(cookie.unchecked_remove(_COOKIE_NEXT))


@api_perm.allow_cookieless_set_user
def api_oauthLogin(simulation_type, oauth_type):
    """Redirects to an OAUTH request for the specified oauth_type ('github').

    If oauth_type is 'anonymous', the current session is cleared.
    """
    sim_type = sirepo.template.assert_sim_type(simulation_type)
    return compat_login(oauth_type, '/{}'.format(sim_type))


def compat_login(oauth_type, oauth_next):
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


def init_apis(app):
    """`init_module` then call `user_state.register_login_module`"""
    init_module(app)
    user_state.register_login_module()


def init_module(app):
    """Used by email_auth to init without registering as login_module.

    Used for backwards compatibility when migrating from GitHub to email_auth.
    """
    assert not UserModel
    _init(app)
    user_db.init(app, _init_user_model)
    user_state.init_beaker_compat()
    uri_router.register_api_module()


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


def _init(app):
#TODO(robnagler) should this be deleted.
    global cfg
    cfg = pkconfig.init(
        github_key=pkconfig.Required(str, 'GitHub application key'),
        github_secret=pkconfig.Required(str, 'GitHub application secret'),
        github_callback_uri=(None, str, 'GitHub application callback URI'),
    )
    app.session_interface = _FlaskSessionInterface()


def _init_user_model(db, base):
    """Creates User class bound to dynamic `db` variable"""
    global User, UserModel

    class User(base, db.Model):
        __tablename__ = 'user_t'
        uid = db.Column(db.String(8), primary_key=True)
        user_name = db.Column(db.String(100), nullable=False)
        display_name = db.Column(db.String(100))
        oauth_type = db.Column(
            db.Enum(DEFAULT_OAUTH_TYPE, 'test', name='oauth_type'),
            nullable=False
        )
        oauth_id = db.Column(db.String(100), nullable=False)
        __table_args__ = (sqlalchemy.UniqueConstraint('oauth_type', 'oauth_id'),)


    UserModel = User
    return User.__tablename__


def _oauth_client(oauth_type):
    if oauth_type == DEFAULT_OAUTH_TYPE:
        return flask_oauthlib.client.OAuth(flask.current_app).remote_app(
            oauth_type,
            consumer_key=cfg.github_key,
            consumer_secret=cfg.github_secret,
            base_url='https://api.github.com/',
            request_token_url=None,
            access_token_method='POST',
            access_token_url='https://github.com/login/oauth/access_token',
            authorize_url='https://github.com/login/oauth/authorize',
        )
    raise RuntimeError('Unknown oauth_type: {}'.format(oauth_type))
