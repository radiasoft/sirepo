# -*- coding: utf-8 -*-
"""oauth for authentication and role moderation

:copyright: Copyright (c) 2022 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern import pkinspect
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp
from sirepo import auth
import authlib.integrations.base_client
import authlib.integrations.requests_client
import sirepo.events
import sirepo.feature_config
import sirepo.sim_oauth
import sirepo.uri_router
import sirepo.util


#: cookie keys for oauth (prefix is "sroa")
_COOKIE_NONCE = "sroan"
_COOKIE_SIM_TYPE = "sroas"


def check_authorized_callback(sapi, github_auth=False):
    # clear temporary cookie values first
    s = sapi.sreq.cookie.unchecked_remove(_COOKIE_NONCE)
    t = sapi.sreq.cookie.unchecked_remove(_COOKIE_SIM_TYPE)
    assert t
    c = _client(t, github_auth)
    try:
        c.fetch_token(
            authorization_response=sapi.sreq.absolute_uri,
            state=s,
            # SECURITY: This *must* be the grant_type otherwise authlib defaults to
            # client_credentials which just returns details about the oauth client. That response
            # can easily be confused for a valid authorization_code response.
            grant_type="authorization_code",
        )

        return c, t
    except Exception as e:
        pkdlog("url={} exception={} stack={}", sapi.sreq.absolute_uri, e, pkdexc())
    sirepo.util.raise_forbidden(f"user denied access from sim_type={t}")


def raise_authorize_redirect(sapi, sim_type, github_auth=False):
    sapi.sreq.cookie.set_value(_COOKIE_SIM_TYPE, sim_type)
    c = _cfg(sim_type, github_auth)
    u, s = _client(sim_type, github_auth).create_authorization_url(c.authorize_url)
    sapi.sreq.cookie.set_value(_COOKIE_NONCE, s)
    raise sirepo.util.Redirect(u)


def _cfg(sim_type, github_auth):
    if github_auth:
        # We are authenticating to sirepo using github oauth
        # or doing jupyter migration.
        from sirepo.auth import github

        return github.cfg
    # We are doing oauth for a sim type
    return sirepo.sim_oauth.import_module(sim_type).cfg


def _client(sim_type, github_auth):
    """Makes it easier to mock, see github_srunit.py"""
    c = _cfg(sim_type, github_auth)
    return authlib.integrations.requests_client.OAuth2Session(
        c.key,
        c.secret,
        redirect_uri=c.callback_uri or sirepo.uri_router.uri_for_api(c.callback_api),
        **c,
    )
