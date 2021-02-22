# -*- coding: utf-8 -*-
u"""Jupyterhub login

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkconfig
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp
import contextlib
import jupyterhub.auth
import sirepo.auth
import sirepo.cookie
import sirepo.server
import sirepo.util
import tornado.web
import werkzeug.exceptions

_JUPYTERHUBLOGIN_ROUTE = '/jupyterhublogin'


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
        with _set_cookie(handler):
            try:
                sirepo.auth.require_user()
                sirepo.auth.require_sim_type('jupyterhublogin')
            except werkzeug.exceptions.Forbidden:
                # returning None means the user is forbidden (403)
                # https://jupyterhub.readthedocs.io/en/stable/api/auth.html#jupyterhub.auth.Authenticator.authenticate
                return None
            except sirepo.util.SRException as e:
                r = e.sr_args.get('routeName')
                if r not in ('completeRegistration', 'login', 'loginFail'):
                    raise
                handler.redirect(f'{_JUPYTERHUBLOGIN_ROUTE}#/{r}')
                raise tornado.web.Finish()
            u = sirepo.sim_api.jupyterhublogin.unchecked_jupyterhub_user_name(
                have_simulation_db=False,
            )
            if not u:
                handler.redirect(f'{_JUPYTERHUBLOGIN_ROUTE}')
                raise tornado.web.Finish()
            return u

    async def refresh_user(self, user, handler=None):
        with _set_cookie(handler):
            try:
                sirepo.auth.require_user()
            except sirepo.util.SRException:
                # Returning False is what the jupyterhub API expects and jupyterhub
                # will handle re-authenticating the user.
                # https://jupyterhub.readthedocs.io/en/stable/api/auth.html#jupyterhub.auth.Authenticator.refresh_user
                return False
            return True


@contextlib.contextmanager
def _set_cookie(handler):
    with sirepo.cookie.set_cookie_outside_of_flask_request(
        handler.get_cookie(sirepo.cookie.cfg.http_name),
    ):
        yield
