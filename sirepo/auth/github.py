# -*- coding: utf-8 -*-
u"""GitHub Login

GitHub is written Github and github (no underscore or dash) for ease of use.

:copyright: Copyright (c) 2016-2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkconfig
from pykern import pkinspect
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp
from sirepo import api_perm
from sirepo import auth
from sirepo import auth_db
from sirepo import cookie
from sirepo import http_request
from sirepo import uri_router
from sirepo import util
import authlib.integrations.flask_client
import flask
import flask.sessions
import sqlalchemy


AUTH_METHOD = 'github'

#: User can see it
AUTH_METHOD_VISIBLE = True

#: Used by auth_db
AuthGithubUser = None

#: Well known alias for auth
UserModel = None

#: module handle
this_module = pkinspect.this_module()

#: cookie keys for github (prefix is "srag")
_COOKIE_NONCE = 'sragn'
_COOKIE_SIM_TYPE = 'srags'


#: cached for _oauth_client
_app = None


@api_perm.allow_cookieless_set_user
def api_authGithubAuthorized():
    """Handle a callback from a successful OAUTH request.

    Tracks oauth users in a database.
    """
    # clear temporary cookie values first
    expect = cookie.unchecked_remove(_COOKIE_NONCE) or '<missing-nonce>'
    t = cookie.unchecked_remove(_COOKIE_SIM_TYPE)
    oc = _oauth_client()
    if not oc.authorize_access_token():
        util.raise_forbidden('missing oauth response')
    got = flask.request.args.get('state', '<missing-state>')
    if expect != got:
        pkdlog(
            'mismatch oauth state: expected {} != got {}',
            expect,
            got,
        )
        auth.login_fail_redirect(t, this_module, 'oauth-state', reload_js=True)
        raise AssertionError('auth.login_fail_redirect returned unexpectedly')
    d = oc.get('user').json()
    with auth_db.thread_lock:
        u = AuthGithubUser.search_by(oauth_id=d['id'])
        if u:
            # always update user_name
            u.user_name = d['login']
        else:
            u = AuthGithubUser(oauth_id=d['id'], user_name=d['login'])
        u.save()
        auth.login(this_module, model=u, sim_type=t, want_redirect=True)
        raise AssertionError('auth.login returned unexpectedly')


@api_perm.require_cookie_sentinel
def api_authGithubLogin(simulation_type):
    """Redirects to Github"""
    req = http_request.parse_params(type=simulation_type)
    s = util.random_base62()
    cookie.set_value(_COOKIE_NONCE, s)
    cookie.set_value(_COOKIE_SIM_TYPE, req.type)
    if not cfg.callback_uri:
        # must be executed in an app and request context so can't
        # initialize earlier.
        cfg.callback_uri = uri_router.uri_for_api('authGithubAuthorized')
    return _oauth_client().authorize_redirect(redirect_uri=cfg.callback_uri, state=s)


@api_perm.allow_cookieless_set_user
def api_oauthAuthorized(oauth_type):
    """Deprecated use `api_authGithubAuthorized`"""
    return api_authGithubAuthorized()


def avatar_uri(model, size):
    return 'https://avatars.githubusercontent.com/{}?size={}'.format(
        model.user_name,
        size,
    )


def init_apis(app, *args, **kwargs):
    global cfg, _app
    cfg = pkconfig.init(
        key=pkconfig.Required(str, 'Github key'),
        secret=pkconfig.Required(str, 'Github secret'),
        callback_uri=(None, str, 'Github callback URI (defaults to api_authGithubAuthorized)'),
    )
    auth_db.init_model(_init_model)
    app.session_interface = _FlaskSessionInterface()
    _app = app


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


def _init_model(base):
    """Creates User class bound to dynamic `db` variable"""
    global AuthGithubUser, UserModel

    class AuthGithubUser(base):
        __tablename__ = 'auth_github_user_t'
        oauth_id = sqlalchemy.Column(sqlalchemy.String(100), primary_key=True)
        user_name = sqlalchemy.Column(sqlalchemy.String(100), unique=True, nullable=False)
        uid = sqlalchemy.Column(sqlalchemy.String(8), unique=True)

    UserModel = AuthGithubUser


def _oauth_client():
    r = authlib.integrations.flask_client.OAuth(_app)
    r.register(
        access_token_params=None,
        access_token_url='https://github.com/login/oauth/access_token',
        api_base_url='https://api.github.com/',
        authorize_params=None,
        authorize_url='https://github.com/login/oauth/authorize',
        client_id=cfg.key,
        client_kwargs={'scope': 'user:email'},
        client_secret=cfg.secret,
        name='github',
    )
    return r.create_client('github')
