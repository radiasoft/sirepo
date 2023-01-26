"""LDAP authentication support
:copyright: Copyright (c) 2022-2023 RadiaSoft LLC.  All Rights Reserved.
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

AUTH_METHOD = "ldap"

AUTH_METHOD_VISIBLE = True

_cfg = None

# ldap dn requires escaped special chars
_ESCAPE_DN_MAIL = re.compile(r"([,\\#<>;\"=+])")

# windows login dialogue char limit for passwords
_MAX_ENTRY = 127

#: module handle
this_module = pkinspect.this_module()

#: Well known alias for auth
user_model = "AuthEmailUser"


class API(sirepo.quest.API):
    @sirepo.quest.Spec("require_cookie_sentinel")
    def api_authLdapLogin(self):
        def _bind(creds):
            try:
                ldap.initialize(_cfg.server).simple_bind_s(creds.dn, creds.password)
            except Exception as e:
                m = "Unable to contact LDAP server"
                if isinstance(e, ldap.INVALID_CREDENTIALS):
                    m = "Incorrect email or password"
                else:
                    pkdlog("email={} exception={}", creds.email, e)
                raise sirepo.util.Response(self.reply_ok(PKDict(formError=m)))

        def _user(email):
            m = self.auth_db.model(user_model)
            u = m.unchecked_search_by(unverified_email=email)
            if not u:
                u = m.new(unverified_email=email, user_name=email)
                u.save()
            return u

        def _validate_entry(creds, field):
            if not creds[field]:
                e = "falsey"
            elif len(creds[field]) > _MAX_ENTRY:
                e = "over max chars"
            else:
                return
            raise sirepo.util.UserAlert(
                "invalid user and/or password",
                "{} field={}; email={}",
                e,
                field,
                creds.email,
            )

        req = self.parse_post()
        res = PKDict(
            email=req.req_data.email,
            password=req.req_data.password,
            dn="mail="
            + re.sub(_ESCAPE_DN_MAIL, r"\\\1", req.req_data.email)
            + _cfg.dn_suffix,
        )
        _validate_entry(res, "email")
        _validate_entry(res, "password")
        _bind(res)
        self.auth.login(
            this_module, sim_type=req.type, model=_user(res.email), want_redirect=True
        )


def init_apis(*args, **kwargs):
    global _cfg

    def _valid_suffix(value):
        if not value:
            e = "falsey"
        elif len(value) > _MAX_ENTRY:
            e = "over max chars"
        else:
            return value
        raise AssertionError(e + " value={}".format(value))

    _cfg = pkconfig.init(
        server=pkconfig.RequiredUnlessDev(
            "ldap://127.0.0.1:389", str, " ldap://ip:port"
        ),
        dn_suffix=pkconfig.RequiredUnlessDev(
            ",ou=users,dc=example,dc=com", _valid_suffix, "ou and dc values of dn"
        ),
    )
