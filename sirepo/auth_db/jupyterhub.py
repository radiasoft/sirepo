# -*- coding: utf-8 -*-
"""sim_api.jupyterhublogin model

:copyright: Copyright (c) 2022 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
import sirepo.auth_db
import sqlalchemy


class JupyterhubUser(sirepo.auth_db.UserDbBase):
    __tablename__ = "jupyterhub_user_t"
    uid = sqlalchemy.Column(sirepo.auth_db.STRING_ID, primary_key=True)
    user_name = sqlalchemy.Column(
        sirepo.auth_db.STRING_NAME,
        nullable=False,
        unique=True,
    )
