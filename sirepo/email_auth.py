# -*- coding: utf-8 -*-
u"""Email login support

:copyright: Copyright (c) 2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function

from flask_sqlalchemy import SQLAlchemy
from pykern import pkcollections
from pykern import pkconfig
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp
from sirepo import api_perm
from sirepo import cookie
from sirepo import http_reply, http_request
from sirepo import server
from sirepo import simulation_db
from sirepo import uri_router
from sirepo import user_db
from sirepo import user_state
from sirepo import util
import datetime
import flask
import flask_mail
import pyisemail
import re
import sirepo.template
import sqlalchemy


#: EmailAuth users most always be non-anonymous
ALLOW_ANONYMOUS_SESSION = False

#: Tell GUI how to authenticate (before schema is loaded)
AUTH_METHOD = 'email'

#: Used by user_db
UserModel = None

#: SIREPO_EMAIL_AUTH_SMTP_SERVER=dev avoids SMTP entirely
_DEV_SMTP_SERVER = 'dev'

#: How to send mail (flask_mail.Mail instance)
_smtp = None

#: how long before token expires
_EXPIRES_MINUTES = 15

#: for adding to now
_EXPIRES_DELTA = datetime.timedelta(minutes=_EXPIRES_MINUTES)


@api_perm.require_user
def api_emailAuthDisplayName():
    data = http_request.parse_json(assert_sim_type=False)
    dn = _parse_display_name(data)
    uid = cookie.get_user()
    assert user_state.is_logged_in(), \
        'user is not logged in, uid={}'.format(uid)
    with user_db.thread_lock:
        user = EmailAuth.search_by(uid=uid)
        user.display_name = data.displayName
        user.save()
    return http_reply.gen_json_ok()


# You have to be an anonymous or logged in user at this point
@api_perm.require_cookie_sentinel
def api_emailAuthLogin():
    data = http_request.parse_json()
    email = _parse_email(data)
    sim_type = sirepo.template.assert_sim_type(data.simulationType)
    with user_db.thread_lock:
        u = EmailAuth.search_by(unverified_email=email)
        if u:
            # might be different uid, but don't care for now, just logout
            user_state.logout_as_user()
        else:
            uid = cookie.unchecked_get_user()
            if uid and not user_state.is_anonymous_session():
                u = EmailAuth.search_by(uid=uid)
                if u:
                    # was logged in as different user so clear and get new user
                    user_state.logout_as_anonymous()
                    uid = None
                else:
### check github, and see if is logged in: then just create email
### record else force github to login; save something in cookie that
### we tried once so we don't loop forever if the user wants to login
### as a different user
                    # is not EmailAuth so must be OAuth
                    user_state.logout_as_user()
                    uid = None
            if not uid:
                uid = simulation_db.user_create()
            u = EmailAuth(uid=uid, unverified_email=email)
        token = u.create_token()
        u.save()
    return _send_login_email(
        u,
        uri_router.uri_for_api(
            'emailAuthorized',
            dict(simulation_type=sim_type, token=token),
        ),
    )


@api_perm.allow_cookieless_set_user
def api_emailAuthorized(simulation_type, token):
    """Clicked by user in an email

    User exists in db, but there user may be logging in via a different
    browser.
    """
    with user_db.thread_lock:
        u = EmailAuth.search_by(token=token)
        if not u or u.expires < datetime.datetime.utcnow():
    ### delete old email record, because not longer valid
            # if the auth is invalid, but the user is already logged in (ie. following an old link from an email)
            # keep the user logged in and proceed to the app
            if _user_with_email_is_logged_in():
                return flask.redirect('/{}'.format(simulation_type))
            if not u:
                pkdlog('login with invalid token: {}', token)
            else:
                pkdlog('login with expired token: {}, email: {}', token, u.unverified_email)
            #TODO(pjm): need uri_router method for this?
            return server.javascript_redirect('/{}#{}'.format(
                simulation_type,
                simulation_db.get_schema(simulation_type).localRoutes.authorizationFailed.route,
            ))
        u.query.filter(
            EmailAuth.user_name == u.unverified_email,
            EmailAuth.unverified_email != u.unverified_email,
        ).delete()
        u.user_name = u.unverified_email
        u.token = None
        u.expires = None
        user_state.login_as_user(u)
#TODO(robnagler) user_state.set_logged_in should do all the work
    return flask.redirect('/{}'.format(simulation_type))


def init_apis(app):
    assert not UserModel
    _init(app)
    user_db.init(app, _init_email_auth_model)
    uri_router.register_api_module()
    user_state.register_login_module()


def _init(app):
    global cfg
    cfg = pkconfig.init(
        smtp_server=pkconfig.Required(str, 'SMTP TLS server'),
        smtp_user=pkconfig.Required(str, 'SMTP auth user'),
        smtp_password=pkconfig.Required(str, 'SMTP auth password'),
        #TODO(robnagler) validate email
        from_email=pkconfig.Required(str, 'From email address'),
        from_name=pkconfig.Required(str, 'From display name'),
    )
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

def _init_email_auth_model(db, base):
    """Creates EmailAuth class bound to dynamic `db` variable"""
    global EmailAuth, UserModel

    # Primary key is unverified_email.
    # New user: (unverified_email, uid, token, expires) -> auth -> (unverified_email, uid, email)
    # Existing user: (unverified_email, token, expires) -> auth -> (unverified_email, uid, email)

    # display_name is prompted after first login

### subclass model passed into _init_email_auth_model
    class EmailAuth(base, db.Model):
        EMAIL_SIZE = 255
        TOKEN_SIZE = 16
        __tablename__ = 'email_auth_t'
        unverified_email = db.Column(db.String(EMAIL_SIZE), primary_key=True)
        uid = db.Column(db.String(8))
        user_name = db.Column(db.String(EMAIL_SIZE), unique=True)
        display_name = db.Column(db.String(100))
        token = db.Column(db.String(TOKEN_SIZE))
        expires = db.Column(db.DateTime())

        def create_token(self):
            token = util.random_base62(self.TOKEN_SIZE)
            self.expires = datetime.datetime.utcnow() + _EXPIRES_DELTA
            self.token = token
            return token


    UserModel = EmailAuth
    return EmailAuth.__tablename__


def _parse_display_name(data):
    res = data.displayName.strip()
    assert len(res), \
        'invalid post data: displayName={}'.format(data.displayName)
    return res


def _parse_email(data):
    res = data.email.lower()
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
    if user_state.is_logged_in():
        user = EmailAuth.search_by(uid=cookie.get_user())
        if user and user.user_name and user.user_name == user.unverified_email:
            return True
    return False
