# -*- coding: utf-8 -*-
u"""Jupyterhub login

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdexc
import jupyterhub.auth
import pykern.pkresource
import requests
import sirepo.server
import tornado.web
import traitlets


def template_dirs():
    return pykern.pkresource.filename('jupyterhub_templates')

class SirepoAuthenticator(jupyterhub.auth.Authenticator):
    # Do not prompt with jupyterhub login page. self.authenticate()
    # will handle login using Sirepo functionality
    # See the jupyterhub docs for more info:
    # https://jupyterhub.readthedocs.io/en/stable/api/auth.html
    auto_login = True
    refresh_pre_spawn = True

    sirepo_uri = traitlets.Unicode(config=True, help='uri to reach sirepo')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        sirepo.server.init()

    async def authenticate(self, handler, data):
        d = self._check_permissions(handler)
        if 'username' in d:
            return d.username
        elif 'uri' in d:
            handler.redirect(d.uri)
            raise tornado.web.Finish()
        # returning None means the user is forbidden (403)
        # https://jupyterhub.readthedocs.io/en/stable/api/auth.html#jupyterhub.auth.Authenticator.authenticate
        return None

    async def refresh_user(self, user, handler=None):
        try:
            return bool(self._check_permissions(handler).get('username'))
        except Exception:
            # Returning False is what the jupyterhub API expects and jupyterhub
            # will handle re-authenticating the user.
            # https://jupyterhub.readthedocs.io/en/stable/api/auth.html#jupyterhub.auth.Authenticator.refresh_user
            return False
        raise AssertionError('should not get here')

    def _check_permissions(self, handler):
        r = requests.post(
            # POSIT: no params on checkAuthJupyterhub
            self.sirepo_uri + sirepo.simulation_db.SCHEMA_COMMON.route.checkAuthJupyterhub,
            cookies={k: handler.get_cookie(k) for k in handler.cookies.keys()},
        )
        r.raise_for_status()
        for k, v in r.cookies.get_dict().items():
            handler.set_cookie(k, v)
        return PKDict(r.json())
