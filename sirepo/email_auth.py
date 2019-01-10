# -*- coding: utf-8 -*-
u"""Email login support

:copyright: Copyright (c) 2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function

from flask_sqlalchemy import SQLAlchemy
from pykern import pkconfig, pkcollections
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp
from sirepo import api_auth
from sirepo import api_perm
from sirepo import cookie
from sirepo import http_reply, http_request
from sirepo import server
from sirepo import simulation_db
from sirepo import uri_router
from sirepo import user_db
from sirepo import user_state
from sirepo import util
import base64
import datetime
import flask
import flask_mail
import hashlib
import sqlalchemy

_AUTH_METHOD = 'email'

# cookie key to track if user's full name has been entered
_COOKIE_DISPLAY_NAME_SET = 'sredn'


def all_uids():
    return user_db.all_uids(UserEmail)


@api_perm.allow_login
def api_emailAuthorized(simulation_type, token):
    user = UserEmail.search_by_token(token)
    if not user or user.expires < datetime.datetime.utcnow():
        # if the auth is invalid, but the user is already logged in (ie. following an old link from an email)
        # keep the user logged in and proceed to the app
        if _user_with_email_is_logged_in():
            return flask.redirect('/{}'.format(simulation_type))
        if not user:
            pkdlog('login with invalid token: {}', token)
        else:
            pkdlog('login with expired token: {}, email: {}', token, user.unverified_email)
        #TODO(pjm): need uri_router method for this?
        return server.javascript_redirect('/{}#{}'.format(
            simulation_type,
            simulation_db.get_schema(simulation_type).localRoutes.authorizationFailed.route,
        ))
    user_db.update_user(UserEmail, {
        'email': user.unverified_email,
        'unverified_email': user.unverified_email,
        'token_hash': None,
        'expires': None,
    })
    user_state.set_logged_in(user.unverified_email)
    if user.display_name:
        cookie.set_value(_COOKIE_DISPLAY_NAME_SET, 1)
    else:
        cookie.unchecked_remove(_COOKIE_DISPLAY_NAME_SET)
    return flask.redirect('/{}'.format(simulation_type))


@api_perm.allow_cookieless_user
def api_emailLogin():
    data = http_request.parse_json()
    user = user_db.find_or_create_user(UserEmail, {
        'unverified_email': data['email'].lower(),
    })
    if not user.email:
        # the user has never successfully logged in, use their current uid if present
        if cookie.has_sentinel() and cookie.has_user_value():
            user.uid = cookie.get_user()
    _send_login_email(
        user,
        uri_router.uri_for_api('emailAuthorized', dict(
            simulation_type=data.simulationType,
            token=user.create_token(),
        )))
    return http_reply.gen_json_ok()


@api_perm.require_user
def api_emailUserName():
    data = http_request.parse_json(assert_sim_type=False)
    user = UserEmail.search_by_uid_and_email(cookie.get_user(), data['email'])
    user.display_name = data.displayName
    user.save()
    cookie.set_value(_COOKIE_DISPLAY_NAME_SET, 1)
    return http_reply.gen_json_ok()


@api_perm.allow_visitor
def api_logout(simulation_type):
    return user_state.process_logout(simulation_type)


def init_apis(app):
    _init(app)
    user_db.init(app, _init_user_email_model)
    uri_router.register_api_module()
    api_auth.register_login_module()


def set_default_state():
    res = user_state.set_default_state(_AUTH_METHOD)
    if cookie.has_key(_COOKIE_DISPLAY_NAME_SET):
        res.display_name_set = cookie.get_value(_COOKIE_DISPLAY_NAME_SET)
    return res


def _init(app):
    global cfg
    cfg = pkconfig.init(
        mail_server=(None, str, 'Mail server'),
        mail_username=(None, str, 'Mail user name'),
        mail_password=(None, str, 'Mail password'),
        mail_from_email=(None, str, 'From email address'),
        mail_from_name=(None, str, 'From email name'),
    )
    assert cfg.mail_server and cfg.mail_username and cfg.mail_password \
        and cfg.mail_from_email and cfg.mail_from_name, 'Missing mail config'
    app.config.update(
        MAIL_USE_TLS=True,
        MAIL_PORT=587,
        MAIL_SERVER=cfg.mail_server,
        MAIL_USERNAME=cfg.mail_username,
        MAIL_PASSWORD=cfg.mail_password,
    )
    global _mail
    _mail = flask_mail.Mail(app)


def _init_user_email_model(_db):
    """Creates UserEmail class bound to dynamic `_db` variable"""
    global UserEmail

    # Primary key is unverified_email.
    # New user: (unverified_email, uid, token_hash, expires) -> auth -> (unverified_email, uid, email)
    # Existing user: (unverified_email, token_hash, expires) -> auth -> (unverified_email, uid, email)

    # display_name is prompted after first login

    class UserEmail(_db.Model):
        EXPIRES_MINUTES = 15
        TOKEN_SIZE = 12
        __tablename__ = 'user_email_t'
        unverified_email = _db.Column(_db.String(500), primary_key=True)
        uid = _db.Column(_db.String(8))
        email = _db.Column(_db.String(500))
        display_name = _db.Column(_db.String(100))
        token_hash = _db.Column(_db.String(100))
        expires = _db.Column(_db.DateTime())

        def __init__(self, uid, user_data):
            self.uid = uid
            self.unverified_email = user_data['unverified_email']

        def create_token(self):
            token = util.random_base62(self.TOKEN_SIZE)
            self.expires = datetime.datetime.utcnow() + datetime.timedelta(minutes=self.EXPIRES_MINUTES)
            self.token_hash = self.hash_token(token)
            self.save()
            return token

        @classmethod
        def hash_token(cls, token):
            h = hashlib.sha256()
            h.update(token)
            return 'v1:' + base64.urlsafe_b64encode(h.digest())

        def save(self):
            _db.session.add(self)
            _db.session.commit()

        @classmethod
        def search(cls, user_data):
            return cls.query.filter_by(unverified_email=user_data['unverified_email']).first()

        @classmethod
        def search_by_token(cls, token):
            return cls.query.filter_by(token_hash=cls.hash_token(token)).first()

        @classmethod
        def search_by_uid(cls, uid):
            return cls.query.filter_by(uid=uid).first()

        @classmethod
        def search_by_uid_and_email(cls, uid, email):
            return cls.query.filter_by(uid=uid, email=email).first()

        def update(self, user_data):
            self.email = user_data['email']
            self.token_hash = user_data['token_hash']
            self.expires = user_data['expires']

    return UserEmail.__tablename__


def _send_login_email(user, url):
    login_text = 'sign in to' if user.email else \
                 'confirm your email and finish creating'
    msg = flask_mail.Message(
        subject='Sign in to Sirepo',
        sender=(cfg.mail_from_name, cfg.mail_from_email),
        recipients=[user.unverified_email],
        body=u'''
Click the link below to {} your Sirepo account.

This link will expire in {} minutes and can only be used once.

{}
'''.format(login_text, UserEmail.EXPIRES_MINUTES, url)
    )
    _mail.send(msg)


def _user_with_email_is_logged_in():
    if user_state.is_logged_in():
        user = UserEmail.search_by_uid(cookie.get_user())
        if user and user.email and user.email == user.unverified_email:
            return True
    return False
