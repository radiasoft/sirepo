# -*- coding: utf-8 -*-
"""Email login

:copyright: Copyright (c) 2018-2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkconfig
from pykern import pkinspect
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp
import hashlib
import pyisemail
import pykern.pkcompat
import sirepo.auth
import sirepo.auth_db
import sirepo.auth_db.email
import sirepo.quest
import sirepo.smtp
import sirepo.srtime
import sirepo.uri
import sirepo.util


AUTH_METHOD = sirepo.auth.METHOD_EMAIL

#: User can see it
AUTH_METHOD_VISIBLE = True

#: Well known alias for auth
UserModel = sirepo.auth_db.AuthEmailUser

#: module handle
this_module = pkinspect.this_module()


class API(sirepo.quest.API):
    @sirepo.quest.Spec("allow_cookieless_set_user", token="EmailAuthToken")
    def api_authEmailAuthorized(self, simulation_type, token):
        """Clicked by user in an email

        Token must exist in db and not be expired.
        """
        if self.sreq.is_spider():
            sirepo.util.raise_forbidden("robots not allowed")
        req = self.parse_params(type=simulation_type)
        with sirepo.util.THREAD_LOCK:
            u = UserModel.search_by(token=token)
            if u and u.expires >= sirepo.srtime.utc_now():
                n = self._verify_confirm(
                    req.type,
                    token,
                    self.auth.need_complete_registration(u),
                )
                UserModel.delete_changed_email(u)
                u.user_name = u.unverified_email
                u.token = None
                u.expires = None
                u.save()
                self.auth.login(this_module, sim_type=req.type, model=u, display_name=n)
                raise AssertionError("auth.login returned unexpectedly")
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
            self.auth.login_fail_redirect(req.type, this_module, "email-token")

    @sirepo.quest.Spec("require_cookie_sentinel", email="Email")
    def api_authEmailLogin(self):
        """Start the login process for the user.

        User has sent an email, which needs to be verified.
        """
        req = self.parse_post()
        email = self._parse_email(req.req_data)
        with sirepo.util.THREAD_LOCK:
            u = UserModel.search_by(unverified_email=email)
            if not u:
                u = UserModel(unverified_email=email)
            u.create_token()
            u.save()
        return self._send_login_email(
            u,
            self.absolute_uri(
                self.uri_for_api(
                    "authEmailAuthorized",
                    dict(simulation_type=req.type, token=u.token),
                ),
            ),
        )

    def _parse_email(self, data):
        res = data.email.strip().lower()
        assert pyisemail.is_email(res), "invalid post data: email={}".format(data.email)
        return res

    def _send_login_email(self, user, uri):
        login_text = (
            "sign in to" if user.user_name else "confirm your email and finish creating"
        )
        r = sirepo.smtp.send(
            recipient=user.unverified_email,
            subject="Sign in to Sirepo",
            body="""
    Click the link below to {} your Sirepo account.

    This link will expire in {} hours and can only be used once.

    {}
    """.format(
                login_text, UserModel.EXPIRES_MINUTES / 60, uri
            ),
        )
        if not r:
            pkdlog("{}", uri)
            return self.reply_ok({"uri": uri})
        return self.reply_ok()

    def _verify_confirm(self, sim_type, token, need_complete_registration):
        m = self.sreq.http_method
        if m == "GET":
            raise sirepo.util.Redirect(
                sirepo.uri.local_route(
                    sim_type,
                    "loginWithEmailConfirm",
                    PKDict(
                        token=token,
                        needCompleteRegistration=need_complete_registration,
                    ),
                ),
            )
        assert m == "POST", "unexpect http method={}".format(m)
        d = self.parse_json()
        if d.get("token") != token:
            raise sirepo.util.Error(
                PKDict(
                    error="unable to confirm login",
                    sim_type=sim_type,
                ),
                "Expected token={} in data but got data.token={}",
                token,
                d,
            )
        return d.get("displayName")


def avatar_uri(qcall, model, size):
    return "https://www.gravatar.com/avatar/{}?d=mp&s={}".format(
        hashlib.md5(pykern.pkcompat.to_bytes(model.user_name)).hexdigest(),
        size,
    )


def unchecked_user_by_user_name(qcall, user_name):
    with sirepo.util.THREAD_LOCK:
        u = UserModel.search_by(user_name=user_name)
        if u:
            return u.uid
        return None
