"""LDAP authentication support

:copyright: Copyright (c) 2022-2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern import pkconfig
from pykern import pkinspect
from pykern.pkdebug import pkdlog, pkdp
from pykern.pkcollections import PKDict
import ldap3
import ldap3.core.exceptions
import pyisemail
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

#: Map ldap3 errors to avoid exposing internals for security reasons
_LDAP3_ERROR = PKDict(
    invalidCredentials=_INVALID_CREDENTIALS,
)


class API(sirepo.quest.API):
    @sirepo.quest.Spec("require_cookie_sentinel")
    async def api_authLdapLogin(self):
        def _bind(creds):
            try:
                ldap3.Connection(
                    ldap3.Server(_cfg.server),
                    user=creds.dn,
                    password=creds.password,
                    auto_escape=True,
                    raise_exceptions=True,
                    read_only=True,
                ).bind()
            except Exception as e:
                m = "Unable to contact LDAP server or unexpected error"
                if isinstance(e, ldap3.core.exceptions.LDAPException) and hasattr(
                    e, "description"
                ):
                    m = _LDAP3_ERROR.get(e.description, m)
                pkdlog("{} user={} dn={}", e, creds.user, creds.dn)
                return m

        def _dn(user):
            return (
                (_cfg.dn_prefix if _cfg.dn_prefix else "")
                + re.sub(_ESCAPE_DN_MAIL, r"\\\1", user)
                + (_cfg.dn_suffix if _cfg.dn_suffix else "")
            )

        def _email(user):
            u = user.lower()
            if "@" not in u:
                if not _cfg.email_domain:
                    raise AssertionError("cfg email_domain must not be None")
                u += "@" + _cfg.email_domain
            if not pyisemail.is_email(u):
                raise AssertionError(
                    f"invalid user={user} or email_domain={_cfg.email_domain}"
                )
            return u

        def _user(email):
            m = self.auth_db.model("AuthEmailUser")
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
            pkdlog("{} field={}; user={}", e, field, creds.user)
            return _INVALID_CREDENTIALS

        req = self.parse_post()
        c = req.req_data.copy()
        c.dn = _dn(c.user)
        if e := (
            _validate_entry(c, "user") or _validate_entry(c, "password") or _bind(c)
        ):
            return self.reply_ok(PKDict(form_error=e))
        self.auth.login(
            this_module,
            sim_type=req.type,
            model=_user(_email(c.user)),
            want_redirect=True,
        )


def _cfg_dn_suffix(value):
    if len(value) > _MAX_ENTRY:
        raise AssertionError(f"value={value} is too long (>{_MAX_ENTRY})")
    return value


def _cfg_email_domain(value):
    # _MAX_ENTRY seems reasonable size
    return _cfg_dn_suffix(value.lower())


def init_apis(*args, **kwargs):
    global _cfg

    _cfg = pkconfig.init(
        dn_prefix=pkconfig.RequiredUnlessDev(
            "mail=",
            str,
            "prefix from username/email of dn (may be None)",
        ),
        dn_suffix=pkconfig.RequiredUnlessDev(
            ",ou=users,dc=example,dc=com",
            _cfg_dn_suffix,
            "ou and dc values of dn (may be None)",
        ),
        # TODO(robnagler) may need to be a map in certain environments
        email_domain=pkconfig.RequiredUnlessDev(
            "example.com",
            str,
            "to enter in auth email db (maybe None if user is an email)",
        ),
        server=pkconfig.RequiredUnlessDev(
            "ldap://127.0.0.1:389",
            str,
            " ldap://ip:port",
        ),
    )
