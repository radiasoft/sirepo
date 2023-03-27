# -*- coding: utf-8 -*-
"""apis for auth

:copyright: Copyright (c) 2022 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
import sirepo.auth
import sirepo.quest
import sirepo.util


class API(sirepo.quest.API):
    @sirepo.quest.Spec("require_cookie_sentinel", display_name="UserDisplayName")
    async def api_authCompleteRegistration(self):
        # Needs to be explicit, because we would need a special permission
        # for just this API.
        if not self.auth.is_logged_in():
            raise sirepo.util.SRException(sirepo.auth.LOGIN_ROUTE_NAME, None)
        self.auth.complete_registration(
            self.auth.parse_display_name(self.parse_json().get("displayName")),
        )
        return self.reply_ok()

    @sirepo.quest.Spec("allow_visitor")
    async def api_authState(self):
        return self.reply_static_jinja(
            "auth-state",
            "js",
            PKDict(auth_state=self.auth.only_for_api_auth_state()),
        )

    @sirepo.quest.Spec("allow_visitor")
    async def api_authState2(self):
        """is alternative to auth_state that returns the JSON struct instead of static JS"""
        a = self.auth.only_for_api_auth_state()
        # only one method is valid, replace visibleMethods array with single value including guest
        assert a["guestIsOnlyMethod"] or len(a["visibleMethods"]) == 1
        m = "guest" if a["guestIsOnlyMethod"] else a["visibleMethods"][0]
        a.pkdel("visibleMethods")
        a.pkupdate({"visibleMethod": m})
        return a

    @sirepo.quest.Spec("allow_visitor")
    async def api_authLogout(self, simulation_type=None):
        """Set the current user as logged out.

        Redirects to root simulation page.
        """
        req = None
        if simulation_type:
            try:
                req = self.parse_params(type=simulation_type)
            except AssertionError:
                pass
        if self.auth.is_logged_in():
            self.auth.only_for_api_logout()
        return self.reply_redirect_for_app_root(req and req.type)


def init_apis(*args, **kwargs):
    from sirepo import auth

    for m in auth.only_for_api_method_modules():
        kwargs["uri_router"].register_api_module(m)
