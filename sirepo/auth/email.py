# -*- coding: utf-8 -*-
u"""Email login

:copyright: Copyright (c) 2018-2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkcollections
from pykern import pkconfig
from pykern import pkinspect
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp
from sirepo import api_perm
from sirepo import auth
from sirepo import http_reply
from sirepo import http_request
from sirepo import uri_router
from sirepo import auth_db
from sirepo import util
import datetime
import flask
import flask_mail
import hashlib
import pyisemail
import re
import sirepo.auth
import sirepo.template
try:
    # py2
    from urllib import urlencode
except ImportError:
    # py3
    from urllib.parse import urlencode

AUTH_METHOD = 'email'

#: User can see it
AUTH_METHOD_VISIBLE = True

#: Used by auth_db
AuthEmailUser = None

#: Well known alias for auth
UserModel = None

#: module handle
this_module = pkinspect.this_module()

#: SIREPO_EMAIL_AUTH_SMTP_SERVER=dev avoids SMTP entirely
_DEV_SMTP_SERVER = 'dev'

#: How to send mail (flask_mail.Mail instance)
_smtp = None

#: how long before token expires
_EXPIRES_MINUTES = 15

#: for adding to now
_EXPIRES_DELTA = datetime.timedelta(minutes=_EXPIRES_MINUTES)


@api_perm.allow_cookieless_set_user
def api_authEmailAuthorized(simulation_type, token):
    """Clicked by user in an email

    Token must exist in db and not be expired.
    """
    t = sirepo.template.assert_sim_type(simulation_type)
    with auth_db.thread_lock:
        u = AuthEmailUser.search_by(token=token)
        if u and u.expires >= datetime.datetime.utcnow():
            u.query.filter(
                (AuthEmailUser.user_name == u.unverified_email),
                AuthEmailUser.unverified_email != u.unverified_email,
            ).delete()
            u.user_name = u.unverified_email
            u.token = None
            u.expires = None
            u.save()
            return auth.login(this_module, sim_type=t, model=u)
        if not u:
            pkdlog('login with invalid token={}', token)
        else:
            pkdlog(
                'login with expired token={}, email={}',
                token,
                u.unverified_email,
            )
        return auth.login_fail_redirect(t, this_module, 'email-token')


@api_perm.require_cookie_sentinel
def api_authEmailLogin():
    """Start the login process for the user.

    User has sent an email, which needs to be verified.
    """
    data = http_request.parse_json()
    email = _parse_email(data)
    t = data.simulationType
    with auth_db.thread_lock:
        u = AuthEmailUser.search_by(unverified_email=email)
        if not u:
            u = AuthEmailUser(unverified_email=email)
        u.token = u.create_token()
        u.save()
    return _send_login_email(
        u,
        uri_router.uri_for_api(
            'authEmailAuthorized',
            dict(simulation_type=t, token=u.token),
        ),
    )


def avatar_uri(model, size):
    return 'https://www.gravatar.com/avatar/{}?d=mp&s={}'.format(
        hashlib.md5(model.user_name).hexdigest(),
        size,
    )


def init_apis(app, *args, **kwargs):
    global cfg
    cfg = pkconfig.init(
        #TODO(robnagler) validate email
        from_email=pkconfig.Required(str, 'From email address'),
        from_name=pkconfig.Required(str, 'From display name'),
        smtp_password=pkconfig.Required(str, 'SMTP auth password'),
        smtp_server=pkconfig.Required(str, 'SMTP TLS server'),
        smtp_user=pkconfig.Required(str, 'SMTP auth user'),
    )
    auth_db.init_model(app, _init_model)
    if pkconfig.channel_in('dev') and cfg.smtp_server == _DEV_SMTP_SERVER:
        return
    app.config.update(
        MAIL_USE_TLS=True,
        MAIL_PORT=587,
        MAIL_SERVER=cfg.smtp_server,
        MAIL_USERNAME=cfg.smtp_user,
        MAIL_PASSWORD=cfg.smtp_password,
    )
    global _smtp
    _smtp = flask_mail.Mail(app)


def _init_model(db, base):
    """Creates AuthEmailUser bound to dynamic `db` variable"""
    global AuthEmailUser, UserModel

    # Primary key is unverified_email.
    # New user: (unverified_email, uid, token, expires) -> auth -> (unverified_email, uid, email)
    # Existing user: (unverified_email, token, expires) -> auth -> (unverified_email, uid, email)

    # display_name is prompted after first login
    class AuthEmailUser(base, db.Model):
        EMAIL_SIZE = 255
        TOKEN_SIZE = 16
        __tablename__ = 'auth_email_user_t'
        unverified_email = db.Column(db.String(EMAIL_SIZE), primary_key=True)
        uid = db.Column(db.String(8), unique=True)
        user_name = db.Column(db.String(EMAIL_SIZE), unique=True)
        token = db.Column(db.String(TOKEN_SIZE), unique=True)
        expires = db.Column(db.DateTime())

        def create_token(self):
            token = util.random_base62(self.TOKEN_SIZE)
            self.expires = datetime.datetime.utcnow() + _EXPIRES_DELTA
            self.token = token
            return token

    UserModel = AuthEmailUser



def _parse_email(data):
    res = data.email.strip().lower()
    assert pyisemail.is_email(res), \
        'invalid post data: email={}'.format(data.email)
    return res


def _send_login_email(user, url):
    if not _smtp:
        assert pkconfig.channel_in('dev')
        pkdlog('{}', url)
        return http_reply.gen_json_ok({'url': url})
    login_text = u'sign in to' if user.user_name else \
        u'confirm your email and finish creating'
    msg = flask_mail.Message(
        subject='Sign in to Sirepo',
        sender=(cfg.from_name, cfg.from_email),
        recipients=[user.unverified_email],
        body=u'''
Click the link below to {} your Sirepo account.

This link will expire in {} minutes and can only be used once.

{}
'''.format(login_text, _EXPIRES_MINUTES, url)
    )
    _smtp.send(msg)
    return http_reply.gen_json_ok()


def _user_with_email_is_logged_in():
    uid = auth.user_if_logged_in(method='email')
    if not uid:
        return None
    u = AuthEmailUser.search_by(uid=uid)
    if u and u.user_name == u.unverified_email:
        return uid
    return None
