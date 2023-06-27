# -*- coding: utf-8 -*-
"""GitHub Login

GitHub is written Github and github (no underscore or dash) for ease of use.

:copyright: Copyright (c) 2016-2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern import pkconfig
from pykern import pkinspect
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp
import sirepo.auth_db
import sirepo.events
import sirepo.oauth
import sirepo.quest
import sqlalchemy


AUTH_METHOD = "github"

this_module = pkinspect.this_module()

#: Well known alias for auth
UserModel = "AuthGithubUser"


class API(sirepo.quest.API):
    @sirepo.quest.Spec("allow_cookieless_set_user")
    async def api_authGithubAuthorized(self):
        """Handle a callback from a successful OAUTH request.

        Tracks oauth users in a database.
        """
        oc, t = sirepo.oauth.check_authorized_callback(self, github_auth=True)
        d = oc.get("https://api.github.com/user").json()
        sirepo.events.emit(self, "github_authorized", PKDict(user_name=d["login"]))
        m = self.auth_db.model(UserModel)
        u = m.unchecked_search_by(oauth_id=d["id"])
        if u:
            # always update user_name
            u.user_name = d["login"]
        else:
            u = m.new(oauth_id=d["id"], user_name=d["login"])
        u.save()
        self.auth.login(
            this_module,
            model=m.unchecked_search_by(oauth_id=d["id"]),
            sim_type=t,
            want_redirect=True,
        )
        raise AssertionError("auth.login returned unexpectedly")

    @sirepo.quest.Spec("require_cookie_sentinel")
    async def api_authGithubLogin(self, simulation_type):
        """Redirects to Github"""
        sirepo.oauth.raise_authorize_redirect(
            self,
            self.parse_params(type=simulation_type).type,
            github_auth=True,
        )

    @sirepo.quest.Spec("allow_cookieless_set_user")
    async def api_oauthAuthorized(self, oauth_type):
        """Deprecated use `api_authGithubAuthorized`"""
        return self.api_authGithubAuthorized()


def avatar_uri(qcall, model, size):
    return "https://avatars.githubusercontent.com/{}?size={}".format(
        model.user_name,
        size,
    )


def _init():
    global cfg, AUTH_METHOD_VISIBLE
    cfg = pkconfig.init(
        authorize_url=(
            "https://github.com/login/oauth/authorize",
            str,
            "url to redirect to for authorization",
        ),
        callback_uri=(
            None,
            str,
            "Github callback URI (defaults to api_authGithubAuthorized)",
        ),
        key=pkconfig.Required(str, "Github key"),
        method_visible=(
            True,
            bool,
            "github auth method is visible to users when it is an enabled method",
        ),
        scope=("user:email", str, "scope of data to request about user"),
        secret=pkconfig.Required(str, "Github secret"),
        token_endpoint=(
            "https://github.com/login/oauth/access_token",
            str,
            "url for obtaining access token",
        ),
    )
    cfg.callback_api = "authGithubAuthorized"

    AUTH_METHOD_VISIBLE = cfg.method_visible


_init()
