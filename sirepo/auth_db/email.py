# -*- coding: utf-8 -*-
"""email auth user

:copyright: Copyright (c) 2022 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
import datetime
import sirepo.auth_db
import sirepo.srtime
import sirepo.util
import sqlalchemy


# Primary key is unverified_email.
# New user: (unverified_email, uid, token, expires) -> auth -> (unverified_email, uid, email)
# Existing user: (unverified_email, token, expires) -> auth -> (unverified_email, uid, email)

#: how long before token expires
_EXPIRES_MINUTES = 8 * 60

#: for adding to now
_EXPIRES_DELTA = datetime.timedelta(minutes=_EXPIRES_MINUTES)


# display_name is prompted after first login
class AuthEmailUser(sirepo.auth_db.UserDbBase):
    EMAIL_SIZE = 255
    EXPIRES_MINUTES = _EXPIRES_MINUTES

    __tablename__ = "auth_email_user_t"
    unverified_email = sqlalchemy.Column(
        sqlalchemy.String(EMAIL_SIZE),
        primary_key=True,
    )
    uid = sqlalchemy.Column(sirepo.auth_db.STRING_ID, unique=True)
    user_name = sqlalchemy.Column(sqlalchemy.String(EMAIL_SIZE), unique=True)
    token = sqlalchemy.Column(sqlalchemy.String(sirepo.util.TOKEN_SIZE), unique=True)
    expires = sqlalchemy.Column(sqlalchemy.DateTime())

    def __init__(self, *args, **kwargs):
        for x in ("unverified_email", "user_name"):
            if (v := kwargs.get(x)) is not None:
                kwargs[x] = v.lower()
        super().__init__(*args, **kwargs)

    def create_token(self):
        self.expires = sirepo.srtime.utc_now() + _EXPIRES_DELTA
        self.token = sirepo.util.create_token(self.unverified_email)

    def delete_changed_email(self, user):
        cls = self.__class__
        self.query().filter(
            (cls.user_name == user.unverified_email),
            cls.unverified_email != user.unverified_email,
        ).delete()

    def unchecked_uid(self, **filter_by):
        u = self.unchecked_search_by(**filter_by)
        if u:
            return u.uid
        return None
