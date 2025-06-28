# -*- coding: utf-8 -*-
"""Email login

:copyright: Copyright (c) 2018-2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern import pkconfig
from pykern import pkinspect
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp
import hashlib
import pyisemail
import pykern.pkcompat
import sirepo.auth
import sirepo.auth_db
import sirepo.auth_role
import sirepo.quest
import sirepo.smtp
import sirepo.srtime
import sirepo.uri
import sirepo.util


AUTH_METHOD = sirepo.auth.METHOD_EMAIL

#: User can see it
AUTH_METHOD_VISIBLE = True

#: Well known alias for auth
UserModel = "AuthEmailUser"

#: module handle
this_module = pkinspect.this_module()

_cfg = None


class API(sirepo.quest.API):

    @sirepo.quest.Spec("require_adm")
    async def api_admUsers(self):
        show_all = self.parse_post().req_data.get("showAll", False)

        def _format_results():
            rows = [
                PKDict(
                    {
                        "Name": u["UserRegistration"].display_name,
                        "Email": u["AuthEmailUser"].unverified_email,
                        "uid": u["UserRole"].uid,
                        "Creation Date": _timestamp(u["UserRegistration"].created),
                        "Role": u["UserRole"].role,
                        "Expiration": _timestamp(u["UserRole"].expiration),
                    }
                )
                for u in _get_user_roles()
            ]
            return PKDict(
                header=list(rows[0].keys()) if len(rows) else [],
                rows=rows,
            )

        def _get_user_roles():
            res = PKDict()
            role_precedence = [
                sirepo.auth_role.ROLE_PLAN_PREMIUM,
                sirepo.auth_role.ROLE_PLAN_BASIC,
                sirepo.auth_role.ROLE_PLAN_TRIAL,
            ]
            for u in _users_from_db():
                assert u["UserRole"].uid == u["UserRegistration"].uid
                uid = u["UserRole"].uid
                r = u["UserRole"].role
                if r not in role_precedence or (
                    uid in res
                    and role_precedence.index(r)
                    > role_precedence.index(res[uid]["UserRole"].role)
                ):
                    continue
                if not show_all:
                    t = _timestamp(u["UserRole"].expiration)
                    if t and t < _timestamp(sirepo.srtime.utc_now()):
                        continue
                res[uid] = u
            return res.values()

        def _timestamp(value):
            return sirepo.srtime.to_timestamp(value) if value else None

        def _users_from_db():
            UserRole, UserRegistration, AuthEmailUser = (
                self.auth_db.model(c).__class__
                for c in ("UserRole", "UserRegistration", "AuthEmailUser")
            )
            return (
                self.auth_db.session()
                .query(
                    UserRole,
                    UserRegistration,
                    AuthEmailUser,
                )
                .select_from(UserRole)
                # TODO(pjm): need to link foreign key uid across tables in sqlalchemy definition
                .join(
                    UserRegistration,
                    UserRole.uid == UserRegistration.uid,
                )
                .join(
                    AuthEmailUser,
                    UserRole.uid == AuthEmailUser.uid,
                )
                .order_by(AuthEmailUser.unverified_email)
                .all()
            )

        return _format_results()

    @sirepo.quest.Spec("allow_cookieless_set_user", token="EmailAuthToken")
    async def api_authEmailAuthorized(self, simulation_type, token):
        """Clicked by user in an email

        Token must exist in db and not be expired.
        """

        def _verify_confirm(sim_type, user):
            m = self.sreq.http_method
            if m == "GET":
                raise sirepo.util.Redirect(
                    sirepo.uri.local_route(
                        sim_type,
                        "loginWithEmailConfirm",
                        PKDict(
                            token=user.token,
                            needCompleteRegistration=self.auth.need_complete_registration(
                                user,
                            ),
                        ),
                    ),
                )
            assert m == "POST", "unexpect http method={}".format(m)
            d = self.body_as_dict()
            if d.get("token") != token:
                raise sirepo.util.Error(
                    "unable to confirm login",
                    "Expected token={} in data but got data.token={}",
                    token,
                    d,
                )
            return d

        if self.sreq.is_spider():
            raise sirepo.util.Forbidden("robots not allowed")
        req = self.parse_params(type=simulation_type)
        m = self.auth_db.model(UserModel)
        u = m.unchecked_search_by(token=token)
        if u and u.expires >= sirepo.srtime.utc_now():
            d = _verify_confirm(req.type, u)
            m.delete_changed_email(user=u)
            u.user_name = u.unverified_email
            u.token = None
            u.expires = None
            u.save()
            self.auth.login(
                this_module,
                sim_type=req.type,
                model=u,
                display_name=d.get("displayName"),
                moderation_reason=d.get("reason"),
            )
        if not u:
            pkdlog("login with invalid token={}", token)
        else:
            pkdlog(
                "login with expired token={}, email={}",
                token,
                u.unverified_email,
            )
        # if user is already logged in via email, then continue to the app
        if self.auth.user_if_logged_in(AUTH_METHOD):
            pkdlog(
                "user already logged in. ignoring invalid token: {}, user: {}",
                token,
                self.auth.logged_in_user(),
            )
            raise sirepo.util.Redirect(sirepo.uri.local_route(req.type))
        self.auth.login_fail_redirect(this_module, "email-token")

    @sirepo.quest.Spec("require_cookie_sentinel", email="Email")
    async def api_authEmailLogin(self):
        """Start the login process for the user.

        User has sent an email, which needs to be verified.
        """

        def _assert_allow(email):
            # POSIT: Email has been validated by _parse_email so simple split is ok
            d = email.split("@")[1]
            if d in _cfg.deny_access_domains:
                raise sirepo.util.InvalidEmail(
                    "invalid email={}",
                    email,
                    sr_args=PKDict(
                        error=f"Please use your institutional email, we do not allow {d} addresses.",
                    ),
                )
            return email

        def _login_text(user_data):
            if user_data.user_name:
                return "sign in to"
            return "confirm your email and finish creating"

        def _parse_email(data):
            res = data.email.strip().lower()
            if not pyisemail.is_email(res):
                raise sirepo.util.InvalidEmail(
                    "invalid email={} ",
                    res,
                    sr_args=PKDict(
                        error="Invalid email. Please update and resubmit.",
                    ),
                )
            return res

        def _send_login_email(user_data, uri):
            if not _send_smtp(user_data, uri):
                pkdlog("{}", uri)
                return self.reply_ok({"uri": uri})
            return self.reply_ok()

        def _send_smtp(user_data, uri):
            return sirepo.smtp.send(
                recipient=user_data.unverified_email,
                subject="Sign in to Sirepo",
                body=f"""
Click the link below to {_login_text(user_data)} your Sirepo account.

This link will expire in {user_data.expires_minutes / 60} hours and can only be used once.

{uri}\n""",
            )

        req = self.parse_post()
        email = _parse_email(req.req_data)
        m = self.auth_db.model(UserModel)
        u = m.unchecked_search_by(unverified_email=email)
        if not u:
            u = m.new(unverified_email=_assert_allow(email))
        u.create_token()
        u.save()
        d = PKDict(
            expires_minutes=u.EXPIRES_MINUTES,
            token=u.token,
            unverified_email=u.unverified_email,
            user_name=u.user_name,
        )
        self.auth_db.commit()
        return _send_login_email(
            d,
            self.absolute_uri(
                self.uri_for_api(
                    "authEmailAuthorized",
                    dict(simulation_type=req.type, token=d.token),
                ),
            ),
        )


def avatar_uri(qcall, model, size):
    return "https://www.gravatar.com/avatar/{}?d=mp&s={}".format(
        hashlib.md5(pykern.pkcompat.to_bytes(model.user_name)).hexdigest(),
        size,
    )


def init_apis(*args, **kwargs):
    global _cfg
    _cfg = pkconfig.init(
        deny_access_domains=(
            set(),
            set,
            "domains that are automatically blocked from email registration",
        ),
    )
