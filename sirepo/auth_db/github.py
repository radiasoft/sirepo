# -*- coding: utf-8 -*-
"""auth.github model

:copyright: Copyright (c) 2022 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
import sirepo.auth_db
import sqlalchemy


class AuthGithubUser(sirepo.auth_db.UserDbBase):
    __tablename__ = "auth_github_user_t"
    oauth_id = sqlalchemy.Column(sirepo.auth_db.STRING_NAME, primary_key=True)
    user_name = sqlalchemy.Column(
        sirepo.auth_db.STRING_NAME,
        unique=True,
        nullable=False,
    )
    uid = sqlalchemy.Column(sirepo.auth_db.STRING_ID, unique=True)
