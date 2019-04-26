# -*- coding: utf-8 -*-
u"""User database support

:copyright: Copyright (c) 2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function

from flask_sqlalchemy import SQLAlchemy
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp
import threading


#: sqlite file located in sirepo_db_dir
_USER_DB_FILE = 'user.db'

#: SQLAlchemy instance
_db = None

#: base for UserRegistration and *User models
UserDbBase = None

#: base for user models
UserRegistration = None

#: Locking of _db calls
thread_lock = threading.RLock()


def all_uids():
    with thread_lock:
        res = set()
        for u in UserRegistration.query.all():
            if u.uid:
                res.add(u.uid)
        return res


def init(app):
    global _db, UserDbBase, UserRegistration
    assert not _db

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

        def delete(self):
            _db.session.delete(self)
            _db.session.commit()

        def save(self):
            _db.session.add(self)
            _db.session.commit()

        @classmethod
        def search_by(cls, **kwargs):
            with thread_lock:
                return cls.query.filter_by(**kwargs).first()

    class UserRegistration(UserDbBase, _db.Model):
        __tablename__ = 'user_registration_t'
        uid = _db.Column(_db.String(8), primary_key=True)
        created = _db.Column(_db.DateTime(), nullable=False)
        display_name = _db.Column(_db.String(100))

    # only creates tables that don't already exist
    _db.create_all()


def init_model(app, callback):
    with thread_lock:
        callback(_db, UserDbBase)
        # only creates tables that don't already exist
        _db.create_all()


def _db_filename(app):
    return app.sirepo_db_dir.join(_USER_DB_FILE)
