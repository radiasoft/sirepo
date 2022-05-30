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
from sirepo import util
import sirepo.api
import sirepo.events
import sirepo.oauth
import sqlalchemy


AUTH_METHOD = 'github'

#: Used by auth_db
AuthGithubUser = None

#: Well known alias for auth
UserModel = None
class API(sirepo.api.Base):
    @api_perm.allow_cookieless_set_user
    def api_authGithubAuthorized(self):
        """Handle a callback from a successful OAUTH request.

        Tracks oauth users in a database.
        """
        oc, t = sirepo.oauth.check_authorized_callback(github_auth=True)
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
            auth.login(
                pkinspect.this_module(),
                model=u,
                sim_type=t,
                want_redirect=True,
            )
            raise AssertionError('auth.login returned unexpectedly')


    @api_perm.require_cookie_sentinel
    def api_authGithubLogin(self, simulation_type):
        """Redirects to Github"""
        raise util.Redirect(sirepo.oauth.create_authorize_redirect(
            self.parse_params(
                    type=simulation_type,
                ).type,
            github_auth=True,
        ))


    @api_perm.allow_cookieless_set_user
    def api_oauthAuthorized(self, oauth_type):
        """Deprecated use `api_authGithubAuthorized`"""
        return self.api_authGithubAuthorized()


def avatar_uri(model, size):
    return 'https://avatars.githubusercontent.com/{}?size={}'.format(
        model.user_name,
        size,
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
        authorize_url=('https://github.com/login/oauth/authorize', str, 'url to redirect to for authorization'),
        callback_uri=(None, str, 'Github callback URI (defaults to api_authGithubAuthorized)'),
        key=pkconfig.Required(str, 'Github key'),
        method_visible=(
            True,
            bool,
            'github auth method is visible to users when it is an enabled method',
        ),
        scope=('user:email', str, 'scope of data to request about user'),
        secret=pkconfig.Required(str, 'Github secret'),
        token_endpoint=('https://github.com/login/oauth/access_token', str, 'url for obtaining access token')
    )
    cfg.callback_api =  'authGithubAuthorized'

    AUTH_METHOD_VISIBLE = cfg.method_visible
    auth_db.init_model(_init_model)


_init()
