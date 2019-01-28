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
_db_serial_lock = threading.RLock()


def all_uids(user_class):
#TODO(robnagler) do we need locking
    res = set()
    for u in user_class.query.all():
        if u.uid:
            res.add(u.uid)
    return res


def find_or_create_user(user_class, user_data):
    with _db_serial_lock:
        user = user_class.search(user_data)
        if not user:
            user = user_class(None, user_data)
        return user


def init(app, callback):
    global _db
    with _db_serial_lock:
        if not _db:
            app.config.update(
                SQLALCHEMY_DATABASE_URI='sqlite:///{}'.format(_db_filename(app)),
                SQLALCHEMY_COMMIT_ON_TEARDOWN=True,
                SQLALCHEMY_TRACK_MODIFICATIONS=False,
            )
            _db = SQLAlchemy(app, session_options=dict(autoflush=True))
        tablename = callback(_db)
        if _db_filename(app).check(file=True):
            engine = _db.get_engine(app)
            if not engine.dialect.has_table(engine.connect(), tablename):
                pkdlog('creating table {} in existing db', tablename)
                _db.create_all()
        else:
            pkdlog('creating user database {}', _db_filename(app))
            _db.create_all()


def update_user(user_class, user_data):
    with _db_serial_lock:
        user = user_class.search(user_data)
        session_uid = cookie.get_user(checked=False)
        if user:
            if session_uid and session_uid != user.uid:
                # check if session_uid is already in the user database, if so, don't copy simulations to new user
                if not user_class.query.filter_by(uid=session_uid).first():
                    simulation_db.move_user_simulations(user.uid)
            user.update(user_data)
            cookie.set_user(user.uid)
        else:
            if not session_uid:
                # ensures the user session (uid) is ready if new user logs in from logged-out session
                pkdlog('creating new session for user: {}', user_data['id'])
                simulation_db.simulation_dir('')
            user = user_class(cookie.get_user(), user_data)
        _db.session.add(user)
        _db.session.commit()


def _db_filename(app):
    return app.sirepo_db_dir.join(_USER_DB_FILE)
