# -*- coding: utf-8 -*-
"""JupyterHub login

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
import tornado.web
import traitlets

SIM_TYPE = "jupyterhublogin"

#: POSIT: avoiding direct import of simulation_db.SCHEMA_COMMON
_CHECK_AUTH_URI = "/check-auth-jupyterhub"
_MISSING_COOKIES_URI_PART = "/missing-cookies"


def template_dirs():
    return pykern.pkresource.filename("jupyterhub_templates")


class SirepoAuthenticator(jupyterhub.auth.Authenticator):
    # Do not prompt with jupyterhub login page. self.authenticate()
    # will handle login using Sirepo functionality
    # See the jupyterhub docs for more info:
    # https://jupyterhub.readthedocs.io/en/stable/api/auth.html
    auto_login = True
    sirepo_uri = traitlets.Unicode(config=True, help="uri to reach sirepo")

    async def authenticate(self, handler, data):
        # returning None means the user is forbidden (403)
        # https://jupyterhub.readthedocs.io/en/stable/api/auth.html#jupyterhub.auth.Authenticator.authenticate
        return self._check_permissions(handler).get("username")

    def _check_permissions(self, handler, should_redirect=True):

        def _cookies(response):
            for k, v in response.cookies.get_dict().items():
                handler.set_cookie(k, v)

        def _handle_unauthenticated(redirect_uri):
            if should_redirect:
                self._redirect(handler, redirect_uri)
                raise AssertionError("self._redirect should always raise")
            raise _UserIsUnauthenticated()

        def _redirect_uri(response):
            m = re.search(
                r'window.location = "(.*)"', pkcompat.from_bytes(response.content)
            )
            return m.group(1) if m else None

        def _request(cookies):
            r = requests.get(
                self.sirepo_uri + _CHECK_AUTH_URI,
                cookies=cookies,
            )
            _cookies(r)
            return r

        r = _request({k: handler.get_cookie(k) for k in handler.cookies.keys()})
        u = _redirect_uri(r)
        if r.status_code == requests.codes.forbidden:
            return PKDict()
        r.raise_for_status()
        if u and _MISSING_COOKIES_URI_PART in u:
            # redirect to /jupyterhublogin which handles missing cookies correctly
            u = f"/{SIM_TYPE}"
        if u:
            _handle_unauthenticated(u)
        res = PKDict(r.json())
        assert "username" in res, f"expected username in response={res}"
        return res

    def _redirect(self, handler, uri):
        handler.redirect(uri)
        raise tornado.web.Finish()


class _UserIsUnauthenticated(Exception):
    pass
