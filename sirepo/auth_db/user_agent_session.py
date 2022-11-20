# -*- coding: utf-8 -*-
"""user agent session

:copyright: Copyright (c) 2022 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
import sirepo.auth_db
import sqlalchemy


class UserAgentSession(sirepo.auth_db.UserDbBase):
    __tablename__ = "user_agent_session_t"
    user_agent_id = sqlalchemy.Column(
        sirepo.auth_db.STRING_ID,
        unique=True,
        primary_key=True,
    )
    login_state = sqlalchemy.Column(sqlalchemy.Boolean(), nullable=False)
    uid = sqlalchemy.Column(sirepo.auth_db.STRING_ID)
    start_time = sqlalchemy.Column(sqlalchemy.DateTime(), nullable=False)
    request_time = sqlalchemy.Column(sqlalchemy.DateTime(), nullable=False)
    # TODO(rorour) enable when using websockets
    # end_time = sqlalchemy.Column(sqlalchemy.DateTime(), nullable=False)
