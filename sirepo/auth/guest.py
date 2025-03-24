# -*- coding: utf-8 -*-
"""Guest login

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern import pkinspect
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp
import sirepo.auth
import sirepo.quest


AUTH_METHOD = sirepo.auth.METHOD_GUEST

#: User can see it
AUTH_METHOD_VISIBLE = True

#: module handle
this_module = pkinspect.this_module()


class API(sirepo.quest.API):
    @sirepo.quest.Spec("require_cookie_sentinel")
    async def api_authGuestLogin(self, simulation_type):
        """You have to be an anonymous or logged in user at this point"""
        req = self.parse_params(type=simulation_type)
        # if already logged in as guest, just redirect
        if self.auth.user_if_logged_in(AUTH_METHOD):
            self.auth.login_success_response(req.type)
        self.auth.login(this_module, sim_type=req.type)
        raise AssertionError("auth.login returned unexpectedly")
