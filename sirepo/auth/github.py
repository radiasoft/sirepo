# -*- coding: utf-8 -*-
u"""GitHub Login

GitHub is written Github and github (no underscore or dash) for ease of use.

:copyright: Copyright (c) 2016-2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern import pkconfig
from pykern import pkinspect
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp
from sirepo import api_perm
from sirepo import auth
from sirepo import auth_db
from sirepo import cookie
from sirepo import feature_config
from sirepo import http_reply
from sirepo import http_request
from sirepo import uri_router
from sirepo import util
import authlib.integrations.requests_client
import authlib.oauth2.rfc6749.errors
import flask
import sirepo.api
import sirepo.events
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


class API(sirepo.api.APIBase):
    @api_perm.allow_cookieless_set_user
    def api_authGithubAuthorized(self):
        """Handle a callback from a successful OAUTH request.
    
        Tracks oauth users in a database.
        """
        # clear temporary cookie values first
        s = cookie.unchecked_remove(_COOKIE_NONCE)
        t = cookie.unchecked_remove(_COOKIE_SIM_TYPE)
        oc = _client()
        try:
            oc.fetch_token(
                authorization_response=flask.request.url,
                state=s,
            )
        except authlib.oauth2.rfc6749.errors.MismatchingStateException:
            auth.login_fail_redirect(t, this_module, 'oauth-state', reload_js=True)
            raise AssertionError('auth.login_fail_redirect returned unexpectedly')
        d = oc.get('https://api.github.com/user').json()
        sirepo.events.emit('github_authorized', PKDict(user_name=d['login']))
        with util.THREAD_LOCK:
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
    def api_authGithubLogin(self, simulation_type):
        """Redirects to Github"""
        req = http_request.parse_params(type=simulation_type)
        s = util.random_base62()
        cookie.set_value(_COOKIE_NONCE, s)
        cookie.set_value(_COOKIE_SIM_TYPE, req.type)
        if not cfg.callback_uri:
            # must be executed in an app and request context so can't
            # initialize earlier.
            cfg.callback_uri = uri_router.uri_for_api('authGithubAuthorized')
        u, _ = _client().create_authorization_url(
            'https://github.com/login/oauth/authorize',
            redirect_uri=cfg.callback_uri,
            state=s,
        )
        return http_reply.gen_redirect(u)
    
    
    @api_perm.allow_cookieless_set_user
    def api_oauthAuthorized(self, oauth_type):
        """Deprecated use `api_authGithubAuthorized`"""
        return api_authGithubAuthorized()


def avatar_uri(model, size):
    return 'https://avatars.githubusercontent.com/{}?size={}'.format(
        model.user_name,
        size,
    )


def _client(token=None):
    """Makes it easier to mock, see github_srunit.py"""
    # OAuth2Session doesn't inherit from OAuth2Mixin for some reason.
    # So, supplying api_base_url has no effect.
    return authlib.integrations.requests_client.OAuth2Session(
        cfg.key,
        cfg.secret,
        scope='user:email',
        token=token,
        token_endpoint='https://github.com/login/oauth/access_token',
    )


def _init():
    def _init_model(base):
        """Creates User class bound to dynamic `db` variable"""
        global AuthGithubUser, UserModel

        class AuthGithubUser(base):
            __tablename__ = 'auth_github_user_t'
            oauth_id = sqlalchemy.Column(base.STRING_NAME, primary_key=True)
            user_name = sqlalchemy.Column(base.STRING_NAME, unique=True, nullable=False)
            uid = sqlalchemy.Column(base.STRING_ID, unique=True)

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


_init()
