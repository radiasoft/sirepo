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

_USER_DB_FILE = 'user.db'

_db = None

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
    global _db, Model

    with thread_lock:
        if not _db:
            app.config.update(
                SQLALCHEMY_DATABASE_URI='sqlite:///{}'.format(_db_filename(app)),
                SQLALCHEMY_COMMIT_ON_TEARDOWN=True,
                SQLALCHEMY_TRACK_MODIFICATIONS=False,
            )
            _db = SQLAlchemy(app, session_options=dict(autoflush=True))

            class Model(_db.Model):

                def __init__(self, **kwargs):
                    for k, v in kwargs.items():
                        setattr(self, k, v)

                def save(self):
                    _db.session.add(self)
                    _db.session.commit()

                @classmethod
                def search_by(cls, **kwargs):
                    with user_db.thread_lock:
                        return cls.query.filter_by(**kwargs).first()

                def login(self, is_anonymous_session):
                    with thread_lock:
                        session_uid = cookie.unchecked_get_user()
                        if session_uid and session_uid != self.uid:
                            # check if session_uid is already in the
                            # user database, if not, copy over simulations
                            # from anonymous to this user.
                            if not self.search_by(uid=session_uid).first():
                                simulation_db.move_user_simulations(self.uid)
                        cookie.set_user(self.uid)

        callback(_db, Model)
###        tablename = callback(_db, Model)
###        if _db_filename(app).check(file=True):
###            engine = _db.get_engine(app)
###            if not engine.dialect.has_table(engine.connect(), tablename):
###                pkdlog('creating table {} in existing db', tablename)
###        else:
###            pkdlog('creating user database {}', _db_filename(app))
        # only creates tables that don't already exist
        _db.create_all()

def _db_filename(app):
    return app.sirepo_db_dir.join(_USER_DB_FILE)
