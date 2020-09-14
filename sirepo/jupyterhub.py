# -*- coding: utf-8 -*-
u"""Jupyterhub login

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkconfig
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdexc
import importlib
import jupyterhub.auth
import os
import sirepo.auth
import sirepo.cookie
import sirepo.server
import sirepo.util
import tornado.web


class Authenticator(jupyterhub.auth.Authenticator):
    # Do not prompt with jupyterhub login page. self.authenticate()
    # will handle login using Sirepo functionality
    auto_login = True
    refresh_pre_spawn = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        sirepo.server.init()

    async def authenticate(self, handler, data):
        c = handler.get_cookie(sirepo.cookie.cfg.http_name)
        if not c:
            c = ''
        sirepo.cookie.set_cookie_for_jupyterhub(f'{sirepo.cookie.cfg.http_name}={c}')
        try:
            sirepo.auth.require_user()
        except sirepo.util.SRException as e:
            r = e.sr_args.get('routeName')
            if r:
                handler.redirect(f'/jupyterhublogin#/{r}')
                raise tornado.web.Finish()
            raise
        u = sirepo.auth.user_if_logged_in()
        assert u, 'expecting user to be logged in'
        # TODO(e-carlin): probably want a different name
        return sirepo.auth.display_name(u)

    async def refresh_user(self, user, handler=None):
        assert handler, \
            'Need the handler to get the cookie'
        c = handler.get_cookie(sirepo.cookie.cfg.http_name)
        if not c:
            return False
        sirepo.cookie.set_cookie_for_jupyterhub(
            f'{sirepo.cookie.cfg.http_name}={c}'
        )

        try:
            sirepo.auth.require_user()
        except sirepo.util.SRException:
            return False
        return True

cfg = pkconfig.init(
    root=('jupyter', str, 'the root path of jupyterhub'),
)
