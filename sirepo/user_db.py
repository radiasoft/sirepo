# -*- coding: utf-8 -*-
u"""User database support

:copyright: Copyright (c) 2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function

from flask_sqlalchemy import SQLAlchemy
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp
from sirepo import cookie
from sirepo import simulation_db
import os.path
import threading

#: sqlite file located in sirepo_db_dir
_USER_DB_FILE = 'user.db'

#: SQLAlchemy instance
_db = None

#: base for user models
UserDbBase = None

#: Locking of _db calls
thread_lock = threading.RLock()


def all_uids(user_class):
    with thread_lock:
        res = set()
        for u in user_class.query.all():
            if u.uid:
                res.add(u.uid)
        return res


def init(app, callback):
    global _db, UserDbBase, UserBase, User

    with thread_lock:
        if not _db:
            app.config.update(
                SQLALCHEMY_DATABASE_URI='sqlite:///{}'.format(_db_filename(app)),
                SQLALCHEMY_COMMIT_ON_TEARDOWN=True,
                SQLALCHEMY_TRACK_MODIFICATIONS=False,
            )
            _db = SQLAlchemy(app, session_options=dict(autoflush=True))


            class UserDbBase(object):
                def __init__(self, **kwargs):
                    for k, v in kwargs.items():
                        setattr(self, k, v)

                def save(self):
                    _db.session.add(self)
                    _db.session.commit()

                @classmethod
                def search_by(cls, **kwargs):
                    with thread_lock:
                        return cls.query.filter_by(**kwargs).first()

            class User(UserDbBase, _db.Model):
                __tablename__ = 'user_t'
                uid = _db.Column(_db.String(8), primary_key=True)
                created = _db.Column(_db.DateTime(), nullable=False)
                display_name = _db.Column(_db.String(100))


            class UserBase(UserDbBase):
                @classmethod
                def create_user(cls, **kwargs):
                    self = cls(**kwargs)
                    if not kwargs.get('uid'):
                        kwargs[uid] = simulation_db.user_create()
                        u = User(
                            uid=self.uid,
                            created=datetime.now(),
                            display_name=None,
                        )
                        _db.session.add(u)
                    return self


        callback(_db, UserDbBase)
        # only creates tables that don't already exist
        _db.create_all()


def _db_filename(app):
    return app.sirepo_db_dir.join(_USER_DB_FILE)
