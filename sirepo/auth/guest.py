# -*- coding: utf-8 -*-
u"""Email login support

:copyright: Copyright (c) 2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function

from flask_sqlalchemy import SQLAlchemy
from pykern import pkcollections
from pykern import pkconfig
from pykern import pkinspect
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
try:
    # py2
    from urllib import urlencode
except ImportError:
    # py3
    from urllib.parse import urlencode


#: User can see it
AUTH_METHOD_VISIBLE = True

#: Used by user_db
UserModel = None

#: module handle
this_module = pkinspect.this_module()

# You have to be an anonymous or logged in user at this point
@api_perm.require_cookie_sentinel
def api_guestAuthLogin():
    pass

def require_user():
    """user_state helper function

    If oauth_compat is on and _COOKIE_OAUTH_COMPAT is set, then
    don't have a user and throw an exception to force a login.
    """
    if cfg.oauth_compat and cookie.has_key(_COOKIE_OAUTH_COMPAT_LOGIN):
        return (
            user_state.LOGGED_OUT_ROUTE_NAME,
            'oauth_compat mode: force login with email_auth'.format(cookie.get_user())
        )
    return None


def _init_email_auth_model(db, base):
    """Creates EmailAuth class bound to dynamic `db` variable"""
    global EmailAuth, UserModel

    # Primary key is unverified_email.
    # New user: (unverified_email, uid, token, expires) -> auth -> (unverified_email, uid, email)
    # Existing user: (unverified_email, token, expires) -> auth -> (unverified_email, uid, email)

    # display_name is prompted after first login

### subclass model passed into _init_email_auth_model
    class EmailAuth(base, db.Model):
        __tablename__ = 'auth_guest_t'
        uid = db.Column(db.String(8), primary_key=True)
        ip = db.Column(db.String(100))

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


def _user_with_email_is_logged_in():
    if user_state.is_logged_in():
        user = EmailAuth.search_by(uid=cookie.get_user())
        if user and user.user_name and user.user_name == user.unverified_email:
            return True
    return False
