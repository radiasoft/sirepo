# -*- coding: utf-8 -*-
u"""OAUTH support

:copyright: Copyright (c) 2016 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkcollections
from pykern import pkconfig
from pykern import pkinspect
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp
from sirepo import api_perm
from sirepo import auth
from sirepo import cookie
from sirepo import uri_router
from sirepo import user_db
from sirepo import util
import flask
import flask.sessions
import flask_oauthlib.client
import sirepo.template

AUTH_METHOD = 'github'

#: User can see it
AUTH_METHOD_VISIBLE = True

#: oauth_type value that should be passed in always
DEFAULT_OAUTH_TYPE = 'github'

#: Used by user_db
AuthGitHubUser = None

#: Well known alias for auth
UserModel = None

#: module handle
this_module = pkinspect.this_module()

# cookie keys for oauth
_COOKIE_NONCE = 'sragn'
_COOKIE_SIM_TYPE = 'srags'


@api_perm.require_cookie_sentinel
def api_oauthAuthorized(oauth_type):
    """Handle a callback from a successful OAUTH request.

    Tracks oauth users in a database.
    """
    _assert_oauth_type(oauth_type)
    with user_db.thread_lock:
        oc = _oauth_client(oauth_type)
        resp = oc.authorized_response()
        if not resp:
            util.raise_forbidden('missing oauth response')
        # clear cookie values
        expect = cookie.unchecked_remove(_COOKIE_NONCE) or '<missing-nonce>'
        sim_type = cookie.unchecked_remove(_COOKIE_SIM_TYPE)
        got = flask.request.args.get('state', '<missing-state>')
        if expect != got:
            pkdlog(
                'mismatch oauth state: expected {} != got {}',
                expect,
                got,
            )
            return auth.login_failed_redirect(sim_type)
        d = oc.get('user', token=(resp['access_token'], '')).data
        u = AuthGitHubUser.search_by(oauth_id=d['id'])
        if u:
            u.user_name = d['login']
        else:
            u = AuthGitHubUser(oauth_id=d['id'], user_name=d['login'])
        u.save()
        return auth.login(
            this_module,
            model=u,
            sim_type=sim_type,
            data=d,
        )


@api_perm.allow_cookieless_set_user
def api_oauthLogin(simulation_type, oauth_type):
    """Redirects to an OAUTH request for the specified oauth_type ('github').
    """
    _assert_oauth_type(oauth_type)
    sim_type = sirepo.template.assert_sim_type(simulation_type)
    state = util.random_base62()
    cookie.set_value(_COOKIE_NONCE, state)
    cookie.set_value(_COOKIE_SIM_TYPE, sim_type)
    callback = cfg.callback_uri
    if not callback:
        callback = uri_router.uri_for_api(
            'oauthAuthorized',
            dict(oauth_type=oauth_type),
        )
    return _oauth_client(oauth_type).authorize(
        callback=callback,
        state=state,
    )


def init_apis(app, *args, **kwargs):
    global cfg
    cfg = pkconfig.init(
        key=pkconfig.Required(str, 'GitHub application key'),
        secret=pkconfig.Required(str, 'GitHub application secret'),
        callback_uri=(None, str, 'GitHub application callback URI'),
    )
    app.session_interface = _FlaskSessionInterface()
    user_db.init_model(app, _init_model)


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


def _assert_oauth_type(t):
    if t != DEFAULT_OAUTH_TYPE:
        raise RuntimeError('Unknown oauth_type={}'.format(t))


def _init_model(db, base):
    """Creates User class bound to dynamic `db` variable"""
    global AuthGitHubUser, UserModel

    class AuthGitHubUser(base, db.Model):
        __tablename__ = 'auth_github_user_t'
        oauth_id = db.Column(db.String(100), primary_key=True)
        user_name = db.Column(db.String(100), unique=True, nullable=False)
        uid = db.Column(db.String(8), unique=True)

    UserModel = AuthGitHubUser


def _oauth_client(oauth_type):
    return flask_oauthlib.client.OAuth(flask.current_app).remote_app(
        oauth_type,
        consumer_key=cfg.key,
        consumer_secret=cfg.secret,
        base_url='https://api.github.com/',
        request_token_url=None,
        access_token_method='POST',
        access_token_url='https://github.com/login/oauth/access_token',
        authorize_url='https://github.com/login/oauth/authorize',
    )
