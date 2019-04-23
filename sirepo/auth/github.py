# -*- coding: utf-8 -*-
u"""GitHub Login

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
from sirepo import user_db
from sirepo import util
import flask
import flask.sessions
import flask_oauthlib.client
import sirepo.template

AUTH_METHOD = 'github'

#: User can see it
AUTH_METHOD_VISIBLE = True

#: Used by user_db
AuthGitHubUser = None

#: Well known alias for auth
UserModel = None

#: module handle
this_module = pkinspect.this_module()

# cookie keys for github
_COOKIE_NONCE = 'sragn'
_COOKIE_SIM_TYPE = 'srags'


@api_perm.allow_cookieless_set_user
def api_authGitHubAuthorized():
    """Handle a callback from a successful OAUTH request.

    Tracks oauth users in a database.
    """
    # clear temporary cookie values first
    expect = cookie.unchecked_remove(_COOKIE_NONCE) or '<missing-nonce>'
    sim_type = cookie.unchecked_remove(_COOKIE_SIM_TYPE)
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
        return auth.login_failed_redirect(sim_type, this_module, 'invalid')
    d = oc.get('user', token=(resp['access_token'], '')).data
    with user_db.thread_lock:
        u = AuthGitHubUser.search_by(oauth_id=d['id'])
        if u:
            # always update user_name
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


@api_perm.require_cookie_sentinel
def api_authGitHubLogin():
    """Redirects to GitHub"""
    d = http_request.parse_json()
    t = sirepo.template.assert_sim_type(d.simulationType)
    s = util.random_base62()
    cookie.set_value(_COOKIE_NONCE, s)
    cookie.set_value(_COOKIE_SIM_TYPE, t)
    return _oauth_client().authorize(callback=cfg.callback_uri, state=s)


@api_perm.allow_cookieless_set_user
def api_oauthAuthorized(oauth_type):
    """Deprecated use `api_authGitHubAuthorized`"""
    return api_authGitHubAuthorized()


def init_apis(app, *args, **kwargs):
    global cfg
    cfg = pkconfig.init(
        key=pkconfig.Required(str, 'GitHub key'),
        secret=pkconfig.Required(str, 'GitHub secret'),
        callback_uri=(None, str, 'GitHub callback URI (defaults to api_authGitHubAuthorized)'),
    )
    app.session_interface = _FlaskSessionInterface()
    user_db.init_model(app, _init_model)


def post_init_uris(*args, **kwargs):
    """Called after uris are initialized"""
    if not cfg.callback_uri:
        cfg.callback_uri = uri_router.uri_for_api('authGitHubAuthorized')


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
    global AuthGitHubUser, UserModel

    class AuthGitHubUser(base, db.Model):
        __tablename__ = 'auth_github_user_t'
        oauth_id = db.Column(db.String(100), primary_key=True)
        user_name = db.Column(db.String(100), unique=True, nullable=False)
        uid = db.Column(db.String(8), unique=True)

    UserModel = AuthGitHubUser


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
