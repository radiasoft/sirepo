# -*- coding: utf-8 -*-
u"""Auth database

:copyright: Copyright (c) 2018-2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function

from flask_sqlalchemy import SQLAlchemy
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp
import threading


#: sqlite file located in sirepo_db_dir
_SQLITE3_BASENAME = 'auth.db'

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

    f = _db_filename(app)
    _migrate_db_file(f)
    app.config.update(
        SQLALCHEMY_DATABASE_URI='sqlite:///{}'.format(f),
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
        _db.create_all()


def _db_filename(app):
    return app.sirepo_db_dir.join(_SQLITE3_BASENAME)


def _migrate_db_file(fn):
    o = fn.new(basename='user.db')
    if not o.exists():
        return
    assert not fn.exists(), \
        'db file collision: old={} and new={} both exist'.format(o, fn)
    try:
        import sqlite3

        c = sqlite3.connect(str(o))
        c.row_factory = sqlite3.Row
        rows = c.execute('SELECT * FROM user_t')
        c2 = sqlite3.connect(str(fn))
        # sqlite3 saves the literal string as the schema
        # so we are formatting it just like SQLAlchemy would
        # format it.
        c2.execute(
            '''CREATE TABLE auth_github_user_t (
        oauth_id VARCHAR(100) NOT NULL,
        user_name VARCHAR(100) NOT NULL,
        uid VARCHAR(8),
        PRIMARY KEY (oauth_id),
        UNIQUE (user_name),
        UNIQUE (uid)
);'''
        )
        for r in rows:
            c2.execute(
                '''
                INSERT INTO auth_github_user_t
                (oauth_id, user_name, uid)
                VALUES (?, ?, ?)
                ''',
                (r['oauth_id'], r['user_name'], r['uid']),
            )
        c.close()
        c2.commit()
        c2.close()
    except sqlite3.OperationalError as e:
        if 'not such table' in e.message:
            return
        raise
    o.rename(o + '-migrated')
    pkdlog('migrated user.db to auth.db')
