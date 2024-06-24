# -*- coding: utf-8 -*-
"""oauth for authentication and role moderation

:copyright: Copyright (c) 2022 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp
import authlib.integrations.base_client
import authlib.integrations.requests_client
import sirepo.feature_config
import sirepo.sim_oauth
import sirepo.uri_router
import sirepo.util


#: cookie keys for oauth (prefix is "sroa")
_COOKIE_NONCE = "sroan"
_COOKIE_SIM_TYPE = "sroas"


def check_authorized_callback(qcall):
    # clear temporary cookie values first
    s = qcall.cookie.unchecked_remove(_COOKIE_NONCE)
    t = qcall.cookie.unchecked_remove(_COOKIE_SIM_TYPE)
    assert t
    qcall.sim_type_set(t)
    c = _client(qcall, t)
    try:
        c.fetch_token(
            authorization_response=qcall.sreq.http_request_uri,
            state=s,
            # SECURITY: This *must* be the grant_type otherwise authlib defaults to
            # client_credentials which just returns details about the oauth client. That response
            # can easily be confused for a valid authorization_code response.
            grant_type="authorization_code",
        )

        return c, t
    except Exception as e:
        pkdlog("url={} exception={} stack={}", qcall.sreq.http_request_uri, e, pkdexc())
    raise sirepo.util.Forbidden(f"user denied access from sim_type={t}")


def raise_authorize_redirect(qcall, sim_type):
    qcall.cookie.set_value(_COOKIE_SIM_TYPE, sim_type)
    c = _cfg(sim_type)
    u, s = _client(qcall, sim_type).create_authorization_url(c.authorize_url)
    qcall.cookie.set_value(_COOKIE_NONCE, s)
    raise sirepo.util.Redirect(u)


def _cfg(sim_type):
    return sirepo.sim_oauth.import_module(sim_type).cfg


def _client(qcall, sim_type):
    """Makes it easier to mock"""
    c = _cfg(sim_type)
    return authlib.integrations.requests_client.OAuth2Session(
        c.key,
        c.secret,
        redirect_uri=c.callback_uri
        or qcall.absolute_uri(sirepo.uri_router.uri_for_api(c.callback_api)),
        **c,
    )
