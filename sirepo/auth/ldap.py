"""LDAP authentication support
:copyright: Copyright (c) 2022-2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern import pkconfig
from pykern import pkinspect
from pykern.pkdebug import pkdlog, pkdp
from pykern.pkcollections import PKDict
from ldap3 import Server, Connection, ALL
from ldap3.core.exceptions import LDAPException
import re
import sirepo.quest
import sirepo.util

AUTH_METHOD = "ldap"

AUTH_METHOD_VISIBLE = True

_cfg = None

# ldap dn requires escaped special chars
_ESCAPE_DN_MAIL = re.compile(r"([,\\#<>;\"=+])")

# windows login dialogue char limit for passwords
_MAX_ENTRY = 127

# shared error for _validate and _bind
_INVALID_CREDENTIALS = "Invalid user and/or password"

#: module handle
this_module = pkinspect.this_module()

#: well known alias for auth
user_model = "AuthEmailUser"


class API(sirepo.quest.API):
    @sirepo.quest.Spec("require_cookie_sentinel")
    async def api_authLdapLogin(self):
        def _bind(creds):
            try:
                server = Server(_cfg.server)
                conn = Connection(
                    server, 
                    user=creds.dn, 
                    password=creds.password, 
                    auto_escape=True, 
                    raise_exceptions=True, 
                    read_only=True
                    )
                conn.bind()
            except Exception as e:
                m = "Unable to contact LDAP server"
                if isinstance(e, LDAPException):
                    m = e.description
                pkdlog("{} email={} dn={}", e, creds.email, creds.dn)
                return m

        def _user(email):
            m = self.auth_db.model(user_model)
            u = m.unchecked_search_by(unverified_email=email)
            if u:
                return u
            u = m.new(unverified_email=email, user_name=email)
            u.save()
            return m.unchecked_search_by(unverified_email=email)

        def _validate_entry(creds, field):
            if not creds[field]:
                e = "falsey"
            elif len(creds[field]) > _MAX_ENTRY:
                e = "over max chars"
            else:
                return
            pkdlog("{} field={}; email={}", e, field, creds.email)
            return _INVALID_CREDENTIALS

        req = self.parse_post()
        dn = _cfg.dn_prefix if _cfg.dn_prefix else ""
        dn += re.sub(_ESCAPE_DN_MAIL, r"\\\1", req.req_data.email)
        dn += _cfg.dn_suffix if _cfg.dn_suffix else ""
        res = PKDict(
            email=req.req_data.email,
            password=req.req_data.password,
            dn=dn
        )
        r = (
            _validate_entry(res, "email")
            or _validate_entry(res, "password")
            or _bind(res)
        )
        if r:
            return self.reply_ok(PKDict(form_error=r))
        self.auth.login(
            this_module, sim_type=req.type, model=_user(res.email), want_redirect=True
        )


def _cfg_dn_suffix(value):
    if len(value) > _MAX_ENTRY:
        raise AssertionError(f"value={value} is too long (>{_MAX_ENTRY})")
    return value


def init_apis(*args, **kwargs):
    global _cfg

    _cfg = pkconfig.init(
        server=(
            "ldap://127.0.0.1:389", str, " ldap://ip:port"
        ),
        dn_suffix=(
            ",ou=users,dc=example,dc=com", _cfg_dn_suffix, "ou and dc values of dn"
        ),
        dn_prefix=(
            "mail=", str, "prefix from username/email of dn"
        ),
    )
