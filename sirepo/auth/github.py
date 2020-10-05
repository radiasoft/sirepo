# -*- coding: utf-8 -*-
u"""GitHub Login

GitHub is written Github and github (no underscore or dash) for ease of use.

:copyright: Copyright (c) 2016-2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkconfig
from pykern import pkinspect
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp
from sirepo import api_perm
from sirepo import auth
from sirepo import auth_db
from sirepo import cookie
from sirepo import events
from sirepo import feature_config
from sirepo import http_reply
from sirepo import http_request
from sirepo import jupyterhub
from sirepo import uri_router
from sirepo import util
import authlib.integrations.base_client
import authlib.integrations.requests_client
import flask
import sqlalchemy


AUTH_METHOD = 'github'

#: Used by auth_db
AuthGithubUser = None

#: Well known alias for auth
UserModel = None

#: module handle
this_module = pkinspect.this_module()

#: cookie keys for github (prefix is "srag")
_COOKIE_NONCE = 'sragn'
_COOKIE_SIM_TYPE = 'srags'


@api_perm.allow_cookieless_set_user
def api_authGithubAuthorized():
    """Handle a callback from a successful OAUTH request.

    Tracks oauth users in a database.
    """
    # clear temporary cookie values first
    oc = _client(cookie.unchecked_remove(_COOKIE_NONCE))
    t = cookie.unchecked_remove(_COOKIE_SIM_TYPE)
    if not oc.authorize_access_token():
        auth.login_fail_redirect(t, this_module, 'oauth-state', reload_js=True)
        raise AssertionError('auth.login_fail_redirect returned unexpectedly')
    d = oc.get('user').json()
    events.emit(events.Type.GITHUB_AUTHORIZED, kwargs=PKDict(user_name=d['login']))
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
    return _client(s).authorize_redirect(redirect_uri=cfg.callback_uri, state=s)


@api_perm.allow_cookieless_set_user
def api_oauthAuthorized(oauth_type):
    """Deprecated use `api_authGithubAuthorized`"""
    return api_authGithubAuthorized()


def avatar_uri(model, size):
    return 'https://avatars.githubusercontent.com/{}?size={}'.format(
        model.user_name,
        size,
    )


def init_apis(*args, **kwargs):

    def _init_model(base):
        """Creates User class bound to dynamic `db` variable"""
        global AuthGithubUser, UserModel

        class AuthGithubUser(base):
            __tablename__ = 'auth_github_user_t'
            oauth_id = sqlalchemy.Column(sqlalchemy.String(100), primary_key=True)
            user_name = sqlalchemy.Column(sqlalchemy.String(100), unique=True, nullable=False)
            uid = sqlalchemy.Column(sqlalchemy.String(8), unique=True)

        UserModel = AuthGithubUser

    global cfg, AUTH_METHOD_VISIBLE
    cfg = pkconfig.init(
        callback_uri=(None, str, 'Github callback URI (defaults to api_authGithubAuthorized)'),
        key=pkconfig.Required(str, 'Github key'),
        method_visible=(
            True,
            bool,
            'github auth method is visible to users when it is an enabled method',
        ),
        secret=pkconfig.Required(str, 'Github secret'),
    )
    AUTH_METHOD_VISIBLE = cfg.method_visible
    auth_db.init_model(_init_model)


def user_name():
    with auth_db.thread_lock:
        return AuthGithubUser.search_by(uid=auth.logged_in_user()).user_name


class _Client(authlib.integrations.base_client.RemoteApp):

    def __init__(self, state):
        super().__init__(
            framework=PKDict(oauth2_client_cls=authlib.integrations.requests_client.OAuth2Session),
            name='github',
            access_token_params=None,
            access_token_url='https://github.com/login/oauth/access_token',
            api_base_url='https://api.github.com/',
            authorize_params=None,
            authorize_url='https://github.com/login/oauth/authorize',
            client_id=cfg.key,
            client_kwargs={'scope': 'user:email'},
            client_secret=cfg.secret,
        )
        self.__state = state

    def authorize_access_token(self):
        assert flask.request.method == 'GET'
        a = self.__state
        assert a
        b = flask.request.args.get('state')
        if a != b:
            pkdlog('mismatch oauth state: expected {} != got {}', a, b)
            return None
        t = self.fetch_access_token(code=flask.request.args['code'], state=b)
        self.token = t
        return t

    def authorize_redirect(self, redirect_uri=None, **kwargs):
        return http_reply.gen_redirect(
            self.create_authorization_url(redirect_uri, **kwargs)['url'],
        )

    def request(self, method, url, token=None, **kwargs):
        if token is None and not kwargs.get('withhold_token'):
            token = self.token
        return super().request(method, url, token=token, **kwargs)


def _client(state):
    """Makes it easier to mock, see github_srunit.py"""
    return _Client(state)
