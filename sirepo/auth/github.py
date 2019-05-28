# -*- coding: utf-8 -*-
u"""GitHub Login

GitHub is written Github and github (no underscore or dash) for ease of use.

:copyright: Copyright (c) 2016-2019 RadiaSoft LLC.  All Rights Reserved.
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
from sirepo import http_request
from sirepo import uri_router
from sirepo import auth_db
from sirepo import util
import flask
import flask.sessions
import flask_oauthlib.client
import sirepo.template

AUTH_METHOD = 'github'

#: User can see it
AUTH_METHOD_VISIBLE = True

#: Used by auth_db
AuthGithubUser = None

#: Well known alias for auth
UserModel = None

#: module handle
this_module = pkinspect.this_module()

# cookie keys for github
_COOKIE_NONCE = 'sragn'
_COOKIE_SIM_TYPE = 'srags'


@api_perm.allow_cookieless_set_user
def api_authGithubAuthorized():
    """Handle a callback from a successful OAUTH request.

    Tracks oauth users in a database.
    """
    # clear temporary cookie values first
    expect = cookie.unchecked_remove(_COOKIE_NONCE) or '<missing-nonce>'
    t = cookie.unchecked_remove(_COOKIE_SIM_TYPE)
    oc = _oauth_client()
    resp = oc.authorized_response()
    if not resp:
        util.raise_forbidden('missing oauth response')
    got = flask.request.args.get('state', '<missing-state>')
    if expect != got:
        pkdlog(
            'mismatch oauth state: expected {} != got {}',
            expect,
            got,
        )
        return auth.login_fail_redirect(t, this_module, 'oauth-state')
    d = oc.get('user', token=(resp['access_token'], '')).data
    with auth_db.thread_lock:
        u = AuthGithubUser.search_by(oauth_id=d['id'])
        if u:
            # always update user_name
            u.user_name = d['login']
        else:
            u = AuthGithubUser(oauth_id=d['id'], user_name=d['login'])
        u.save()
        return auth.login(
            this_module,
            model=u,
            sim_type=t,
            data=d,
        )


@api_perm.require_cookie_sentinel
def api_authGithubLogin(simulation_type):
    """Redirects to Github"""
    t = sirepo.template.assert_sim_type(simulation_type)
    s = util.random_base62()
    cookie.set_value(_COOKIE_NONCE, s)
    cookie.set_value(_COOKIE_SIM_TYPE, t)
    if not cfg.callback_uri:
        # must be executed in an app and request context so can't
        # initialize earlier.
        cfg.callback_uri = uri_router.uri_for_api('authGithubAuthorized')
    return _oauth_client().authorize(callback=cfg.callback_uri, state=s)


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
    global cfg
    cfg = pkconfig.init(
        key=pkconfig.Required(str, 'Github key'),
        secret=pkconfig.Required(str, 'Github secret'),
        callback_uri=(None, str, 'Github callback URI (defaults to api_authGithubAuthorized)'),
    )
    app.session_interface = _FlaskSessionInterface()
    auth_db.init_model(app, _init_model)


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


def _init_model(db, base):
    """Creates User class bound to dynamic `db` variable"""
    global AuthGithubUser, UserModel

    class AuthGithubUser(base, db.Model):
        __tablename__ = 'auth_github_user_t'
        oauth_id = db.Column(db.String(100), primary_key=True)
        user_name = db.Column(db.String(100), unique=True, nullable=False)
        uid = db.Column(db.String(8), unique=True)

    UserModel = AuthGithubUser


def _oauth_client():
    return flask_oauthlib.client.OAuth(flask.current_app).remote_app(
        'github',
        consumer_key=cfg.key,
        consumer_secret=cfg.secret,
        base_url='https://api.github.com/',
        request_token_url=None,
        access_token_method='POST',
        access_token_url='https://github.com/login/oauth/access_token',
        authorize_url='https://github.com/login/oauth/authorize',
    )
