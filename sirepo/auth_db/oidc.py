"""Pending OpenID Connect authorization requests.

:copyright: Copyright (c) 2026 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

import sirepo.auth_db
import sqlalchemy


class AuthOidcLogin(sirepo.auth_db.UserDbBase):
    __tablename__ = "auth_oidc_login_t"
    state = sqlalchemy.Column(sqlalchemy.String(64), primary_key=True)
    nonce = sqlalchemy.Column(sqlalchemy.String(64), nullable=False)
    verifier = sqlalchemy.Column(sqlalchemy.String(128), nullable=False)
    simulation_type = sqlalchemy.Column(sqlalchemy.String(100), nullable=False)
    expires = sqlalchemy.Column(sqlalchemy.DateTime(), nullable=False)
    email = sqlalchemy.Column(sqlalchemy.String(255))
    guest_uid = sqlalchemy.Column(sirepo.auth_db.STRING_ID)
    consumed = sqlalchemy.Column(sqlalchemy.Boolean, nullable=False, default=False)
