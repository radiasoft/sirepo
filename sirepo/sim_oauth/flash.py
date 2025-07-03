# -*- coding: utf-8 -*-
"""Oauth API's for flash sim

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern import pkconfig
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp
import datetime
import sirepo.quest
import sirepo.auth_role
import sirepo.oauth
import sirepo.srtime
import sirepo.util

cfg = None

_SIM_TYPE = "flash"


class API(sirepo.quest.API):
    @sirepo.quest.Spec("require_plan")
    async def api_simOauthFlashAuthorized(self):
        o, _ = sirepo.oauth.check_authorized_callback(self)
        i = PKDict(o.get(cfg.info_url).json())
        # TODO(robnagler) should this not raise forbidden?
        assert (
            i.status == cfg.info_valid_user
        ), f"unexpected status in info={i} expect={cfg.info_valid_user}"
        self.auth_db.model("UserRole").add_roles(
            [sirepo.auth_role.for_sim_type(_SIM_TYPE)],
            uid=self.logged_in_user(check_path=False),
            expiration=datetime.datetime.fromtimestamp(PKDict(o.token).expires_at),
        )
        raise sirepo.util.Redirect(self.uri_for_app_root(_SIM_TYPE))


def init_apis(*args, **kwargs):
    global cfg
    cfg = pkconfig.init(
        authorize_url=(
            "https://flash.rochester.edu/id/oauth2/auth",
            str,
            "url to redirect to for authorization",
        ),
        callback_uri=(
            None,
            str,
            "Flash callback URI (defaults to api_simOauthFlashAuthorized)",
        ),
        info_valid_user=pkconfig.Required(str, "valid user status code"),
        info_url=(
            "https://flash.rochester.edu/id/userinfo",
            str,
            "to request user data",
        ),
        key=pkconfig.Required(str, "OAuth key"),
        scope=("openid", str, "scope of data to request about user"),
        secret=pkconfig.Required(str, "OAuth secret"),
        token_endpoint=(
            "https://flash.rochester.edu/id/oauth2/token",
            str,
            "url for obtaining access token",
        ),
    )
    cfg.callback_api = "simOauthFlashAuthorized"
