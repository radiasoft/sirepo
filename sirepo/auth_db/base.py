# -*- coding: utf-8 -*-
"""

:copyright: Copyright (c) 2022 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
import sirepo.auth_db
import sqlalchemy


class DbUpgrade(sirepo.auth_db.UserDbBase):
    __tablename__ = "db_upgrade_t"
    name = sqlalchemy.Column(sirepo.auth_db.STRING_NAME, primary_key=True)
    created = sqlalchemy.Column(sqlalchemy.DateTime(), nullable=False)
