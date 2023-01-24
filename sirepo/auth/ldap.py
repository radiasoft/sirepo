"""LDAP authentication support
:copyright: Copyright (c) 2018-2022 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern import pkconfig
from pykern import pkinspect
from pykern.pkdebug import pkdlog, pkdp
from pykern.pkcollections import PKDict
import ldap
import re
import sirepo.quest
import sirepo.util

# TODO(BG): Write test

AUTH_METHOD = "ldap"

AUTH_METHOD_VISIBLE = True

_cfg = None

_ESCAPE_DN_MAIL = re.compile(r'([,\\#<>;\"=+])')

#: module handle
this_module = pkinspect.this_module()

#: Well known alias for auth
user_model = "AuthEmailUser"

class API(sirepo.quest.API):
    @sirepo.quest.Spec("require_cookie_sentinel")
    def api_authLdapLogin(self):

        # validates username/password, escapes special chars for ldap dn
        def _validate_escape_credentials(req):
            email = req.req_data.email.lower()
            if (len(email) > 256 or len(req.req_data.password) > 256):
                raise sirepo.util.UserAlert(
                    "invalid user and/or password",
                    f"email={email} or password greater than 256 chars",
                )
            if (not email or not req.req_data.password):
                raise sirepo.util.UserAlert(
                    "invalid user and/or password",
                    f"email={email} or password is none/zero length",
                )
            return ("mail=" + re.sub(_ESCAPE_DN_MAIL, r"\\\1", email) + _cfg.base_dn, email, req.req_data.password)

        def _authorize_ldap(dn,email,p):

            try:
                c = ldap.initialize(_cfg.ldap_server)
                c.simple_bind_s(dn, p)
            except Exception as e:
                m = "Unable to contact LDAP server"
                if isinstance(e, ldap.INVALID_CREDENTIALS):
                    m = "Incorrect email or password"
                else:
                    pkdlog("email={} exception={}", email, e)
                raise sirepo.util.Response(self.reply_ok(PKDict(formError=m)))

        def _user(email):
            m = self.auth_db.model(user_model)
            u = m.unchecked_search_by(unverified_email=email)
            if not u:
                u = m.new(unverified_email=email, user_name=email)
                u.save()
            return u

        req = self.parse_post()
        (dn, e, p) = _validate_escape_credentials(req)
        _authorize_ldap(dn, e, p)
        self.auth.login(this_module, sim_type=req.type, model=_user(e), want_redirect=True)

def init_apis(*args, **kwargs):
    global _cfg
    _cfg = pkconfig.init(
        ldap_server=("ldap://10.10.10.10:389", str, " ldap://ip:port"),
        base_dn=(",ou=users,dc=example,dc=com", str, "ou and dc values of DN"),
    )
