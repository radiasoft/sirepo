# -*- coding: utf-8 -*-
u"""Jupyterhub login

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern import pkcompat
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdexc
import jupyterhub.auth
import pykern.pkresource
import re
import requests
import sirepo.server
import tornado.web
import traitlets

_SIM_TYPE = 'jupyterhublogin'

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
        # returning None means the user is forbidden (403)
        # https://jupyterhub.readthedocs.io/en/stable/api/auth.html#jupyterhub.auth.Authenticator.authenticate
        return self._check_permissions(handler).get('username')

    async def refresh_user(self, user, handler=None):
        # Reading jupyterhub code the handler is never None
        # We need the handler for cookies and redirects
        assert handler, \
            'handler should never be none'
        # Returning True/False is what the jupyterhub API expects and jupyterhub
        # will handle re-authenticating the user if needed.
        # https://jupyterhub.readthedocs.io/en/stable/api/auth.html#jupyterhub.auth.Authenticator.refresh_user
        return bool(self._check_permissions(handler).get('username'))

    def _check_permissions(self, handler):
        def _cookies(response):
            for k, v in response.cookies.get_dict().items():
                handler.set_cookie(k, v)


        def _maybe_html_redirect(response):
            m = re.search(r'window.location = "(.*)"', pkcompat.from_bytes(response.content))
            m and self._redirect(handler, m.group(1))

        def _maybe_srexception_redirect(response):
            if 'srException' not in response:
                return
            from sirepo import uri
            e = PKDict(response.srException)
            self._redirect(
                handler,
                uri.local_route(
                    _SIM_TYPE,
                    route_name=e.routeName,
                    params=e.params,
                    external=False,
                )
            )

        r = requests.post(
            # POSIT: no params on checkAuthJupyterhub
            self.sirepo_uri + sirepo.simulation_db.SCHEMA_COMMON.route.checkAuthJupyterhub,
            cookies={k: handler.get_cookie(k) for k in handler.cookies.keys()},
        )
        _cookies(r)
        if r.status_code == requests.codes.forbidden:
            return PKDict()
        r.raise_for_status()
        _maybe_html_redirect(r)
        res = PKDict(r.json())
        _maybe_srexception_redirect(res)
        assert 'username' in res, \
            f'unexpected response={res}'
        return res

    def _redirect(self, handler, uri):
        handler.redirect(uri)
        raise tornado.web.Finish()
