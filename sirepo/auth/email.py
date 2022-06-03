# -*- coding: utf-8 -*-
u"""Email login

:copyright: Copyright (c) 2018-2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkcompat
from pykern import pkconfig
from pykern import pkinspect
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp
from sirepo import api_perm
from sirepo import auth
from sirepo import auth_db
from sirepo import http_reply
from sirepo import http_request
from sirepo import smtp
from sirepo import srtime
from sirepo import uri_router
import datetime
import flask
import hashlib
import pyisemail
import sirepo.request
import sirepo.template
import sirepo.uri
import sirepo.util
import sqlalchemy


AUTH_METHOD = 'email'

#: User can see it
AUTH_METHOD_VISIBLE = True

#: Used by auth_db
AuthEmailUser = None

#: Well known alias for auth
UserModel = None

#: module handle
this_module = pkinspect.this_module()

#: how long before token expires
_EXPIRES_MINUTES = 8 * 60

#: for adding to now
_EXPIRES_DELTA = datetime.timedelta(minutes=_EXPIRES_MINUTES)


class Request(sirepo.request.Base):
    @api_perm.allow_cookieless_set_user
    def api_authEmailAuthorized(self, simulation_type, token):
        """Clicked by user in an email
    
        Token must exist in db and not be expired.
        """
        if http_request.is_spider():
            sirepo.util.raise_forbidden('robots not allowed')
        req = self.parse_params(type=simulation_type)
        with sirepo.util.THREAD_LOCK:
            u = AuthEmailUser.search_by(token=token)
            if u and u.expires >= srtime.utc_now():
                n = self._verify_confirm(req.type, token, auth.need_complete_registration(u))
                AuthEmailUser.delete_changed_email(u)
                u.user_name = u.unverified_email
                u.token = None
                u.expires = None
                u.save()
                auth.login(this_module, sim_type=req.type, sreq=self, model=u, display_name=n)
                raise AssertionError('auth.login returned unexpectedly')
            if not u:
                pkdlog('login with invalid token={}', token)
            else:
                pkdlog(
                    'login with expired token={}, email={}',
                    token,
                    u.unverified_email,
                )
            # if user is already logged in via email, then continue to the app
            if auth.user_if_logged_in(AUTH_METHOD):
                pkdlog(
                    'user already logged in. ignoring invalid token: {}, user: {}',
                    token,
                    auth.logged_in_user(),
                )
                raise sirepo.util.Redirect(sirepo.uri.local_route(req.type))
            auth.login_fail_redirect(req.type, this_module, 'email-token')
    
    
    @api_perm.require_cookie_sentinel
    def api_authEmailLogin(self):
        """Start the login process for the user.
    
        User has sent an email, which needs to be verified.
        """
        req = self.parse_post()
        email = self._parse_email(req.req_data)
        with sirepo.util.THREAD_LOCK:
            u = AuthEmailUser.search_by(unverified_email=email)
            if not u:
                u = AuthEmailUser(unverified_email=email)
            u.create_token()
            u.save()
        return self._send_login_email(
            u,
            uri_router.uri_for_api(
                'authEmailAuthorized',
                dict(simulation_type=req.type, token=u.token),
            ),
        )

    def _parse_email(self, data):
        res = data.email.strip().lower()
        assert pyisemail.is_email(res), \
            'invalid post data: email={}'.format(data.email)
        return res

    def _send_login_email(self, user, uri):
        login_text = u'sign in to' if user.user_name else \
            u'confirm your email and finish creating'
        r = smtp.send(
            recipient=user.unverified_email,
            subject='Sign in to Sirepo',
            body=u'''
    Click the link below to {} your Sirepo account.
    
    This link will expire in {} hours and can only be used once.
    
    {}
    '''.format(login_text, _EXPIRES_MINUTES / 60, uri)
        )
        if not r:
            pkdlog('{}', uri)
            return self.reply_ok({'uri': uri})
        return self.reply_ok()

    def _verify_confirm(self, sim_type, token, need_complete_registration):
        m = flask.request.method
        if m == 'GET':
            raise sirepo.util.Redirect(
                sirepo.uri.local_route(
                    sim_type,
                    'loginWithEmailConfirm',
                    PKDict(
                        token=token,
                        needCompleteRegistration=need_complete_registration,
                    ),
                ),
            )
        assert m == 'POST', 'unexpect http method={}'.format(m)
        d = self.parse_json()
        if d.get('token') != token:
            raise sirepo.util.Error(
                PKDict(
                    error='unable to confirm login',
                    sim_type=sim_type,
                ),
                'Expected token={} in data but got data.token={}',
                token,
                d,
            )
        return d.get('displayName')


def avatar_uri(model, size):
    return 'https://www.gravatar.com/avatar/{}?d=mp&s={}'.format(
        hashlib.md5(pkcompat.to_bytes(model.user_name)).hexdigest(),
        size,
    )


def unchecked_user_by_user_name(user_name):
    with sirepo.util.THREAD_LOCK:
       u = AuthEmailUser.search_by(user_name=user_name)
       if u:
           return u.uid
       return None


def _init_model(base):
    """Creates AuthEmailUser bound to dynamic `db` variable"""
    global AuthEmailUser, UserModel

    # Primary key is unverified_email.
    # New user: (unverified_email, uid, token, expires) -> auth -> (unverified_email, uid, email)
    # Existing user: (unverified_email, token, expires) -> auth -> (unverified_email, uid, email)

    # display_name is prompted after first login
    class AuthEmailUser(base):
        EMAIL_SIZE = 255
        __tablename__ = 'auth_email_user_t'
        unverified_email = sqlalchemy.Column(sqlalchemy.String(EMAIL_SIZE), primary_key=True)
        uid = sqlalchemy.Column(base.STRING_ID, unique=True)
        user_name = sqlalchemy.Column(sqlalchemy.String(EMAIL_SIZE), unique=True)
        token = sqlalchemy.Column(sqlalchemy.String(sirepo.util.TOKEN_SIZE), unique=True)
        expires = sqlalchemy.Column(sqlalchemy.DateTime())

        def create_token(self):
            self.expires = srtime.utc_now() + _EXPIRES_DELTA
            self.token = sirepo.util.create_token(self.unverified_email)

        @classmethod
        def delete_changed_email(cls, user):
            with sirepo.util.THREAD_LOCK:
                cls._session().query(cls).filter(
                    (cls.user_name == user.unverified_email),
                    cls.unverified_email != user.unverified_email
                ).delete()
                cls._session().commit()

    UserModel = AuthEmailUser





auth_db.init_model(_init_model)
