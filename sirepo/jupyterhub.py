# -*- coding: utf-8 -*-
u"""Jupyterhub login

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkconfig
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp
import jupyterhub.auth
import sirepo.auth
import sirepo.cookie
import sirepo.server
import sirepo.util
import tornado.web


class Authenticator(jupyterhub.auth.Authenticator):
    # Do not prompt with jupyterhub login page. self.authenticate()
    # will handle login using Sirepo functionality
    # See the jupyterhub docs for more info:
    # https://jupyterhub.readthedocs.io/en/stable/api/auth.html
    auto_login = True
    refresh_pre_spawn = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        sirepo.server.init()

    async def authenticate(self, handler, data):
        _set_cookie(handler)
        try:
            sirepo.auth.require_user()
        except sirepo.util.SRException as e:
            r = e.sr_args.get('routeName')
            if r:
                handler.redirect(f'/jupyterhublogin#/{r}')
                raise tornado.web.Finish()
            raise
        # Do not check path. If not found will result in updates to db
        # which we can not lock.
        u = sirepo.sim_api.jupyterhublogin.logged_in_user_name(check_path=False)
        if not u:
            handler.redirect(f'/jupyterhublogin')
            raise tornado.web.Finish()
        return u

    async def refresh_user(self, user, handler=None):
        _set_cookie(handler)
        try:
            sirepo.auth.require_user()
        except sirepo.util.SRException:
            return False
        return True


def _set_cookie(handler):
    sirepo.cookie.set_cookie_for_utils(
        handler.get_cookie(sirepo.cookie.cfg.http_name),
    )
