"""Authentication by a trusted reverse proxy.

:copyright: Copyright (c) 2019 Bivio Software, Inc.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern import pkconfig
from pykern import pkinspect
import hmac
import re
import sirepo.feature_config
import sirepo.quest
import sirepo.util
import tornado.httputil


AUTH_METHOD = "header"

AUTH_METHOD_VISIBLE = True

UserModel = "AuthEmailUser"

this_module = pkinspect.this_module()

_cfg = None


class API(sirepo.quest.API):
    @sirepo.quest.Spec("allow_cookieless_set_user")
    async def api_authHeaderLogin(self, simulation_type):
        req = self.parse_params(type=simulation_type)
        authenticate(self, req.type)


def authenticate(qcall, sim_type):
    """Complete the proxy handoff, preserving an existing header-auth session."""
    if qcall.auth.user_if_logged_in(AUTH_METHOD):
        qcall.auth.login_success_response(sim_type, want_redirect=True)
    t = qcall.sreq.header_uget(_cfg.token_header)
    n = qcall.sreq.header_uget(_cfg.username_header)
    if not t or not hmac.compare_digest(t.encode("utf-8"), _cfg.tkn.encode("utf-8")):
        raise sirepo.util.Forbidden("missing or invalid proxy authentication token")
    m = qcall.auth_db.model(UserModel)
    if (
        not n
        or len(n) > m.EMAIL_SIZE
        or not n.isprintable()
        or any(c.isspace() or c == "," for c in n)
    ):
        raise sirepo.util.Forbidden("missing or invalid proxy username")
    n = n.lower()
    u = m.unchecked_search_by(user_name=n)
    if not u:
        u = m.unchecked_search_by(unverified_email=n)
        if u:
            if u.user_name is not None:
                raise sirepo.util.Forbidden("proxy username conflicts with an account")
            u.user_name = n
        else:
            u = m.new(unverified_email=n, user_name=n)
        u.save()
    if (
        sirepo.feature_config.cfg().is_registration_moderated
        and qcall.auth.need_complete_registration(u)
    ):
        raise sirepo.util.Forbidden(
            "proxy authentication requires an existing registered account "
            "when registration is moderated"
        )
    # Proxy login must not inherit an account authenticated by another method.
    qcall.auth.reset_state()
    qcall.auth.login(this_module, model=u, sim_type=sim_type, want_redirect=True)


def init_apis(*args, **kwargs):
    global _cfg

    _cfg = pkconfig.init(
        logout_url=(None, str, "Proxy logout URL to visit after Sirepo logout"),
        tkn=pkconfig.Required(str, "Shared secret supplied only by the trusted proxy"),
        token_header=("X-Sirepo-Auth-Token", _cfg_header, "Proxy shared-secret header"),
        username_header=(
            "X-Sirepo-User",
            _cfg_header,
            "Authenticated proxy username header",
        ),
    )
    if _cfg.token_header.lower() == _cfg.username_header.lower():
        raise AssertionError("proxy username and token headers must be different")


def logout_url():
    return _cfg.logout_url


def _cfg_header(value):
    if not re.fullmatch(r"[!#$%&'*+.^_`|~0-9A-Za-z-]+", value) or value.lower() in (
        "authorization",
        "cookie",
    ):
        raise AssertionError("invalid proxy authentication header name")
    # WebSocket requests retain Tornado's canonical names in a case-sensitive dict.
    return next(iter(tornado.httputil.HTTPHeaders({value: ""})))
