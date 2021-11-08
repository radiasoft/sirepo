# -*- coding: utf-8 -*-
u"""Auth database

:copyright: Copyright (c) 2018-2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp
import contextlib
import sqlalchemy
import sqlalchemy.ext.declarative
import sqlalchemy.orm
# limit imports here
import sirepo.auth_role
import sirepo.srcontext
import sirepo.srdb
import sirepo.util


#: sqlite file located in sirepo_db_dir
_SQLITE3_BASENAME = 'auth.db'

_SRCONTEXT_SESSION_KEY = 'auth_db_session'

#: SQLAlchemy database engine
_engine = None

#: Keeps track of upgrades applied to the database
DbUpgrade = None

#: base for UserRegistration and *User models
UserDbBase = None

#: base for user models
UserRegistration = None

#: roles for each user
UserRole = None


def all_uids():
    return UserRegistration.search_all_for_column('uid')


def audit_proprietary_lib_files(uid, force=False, sim_types=None):
    """Add/removes proprietary files based on a user's roles

    For example, add the Flash tarball if user has the flash role.

    Args:
      uid (str): The uid of the user to audit
      force (bool): Overwrite existing lib files with the same name as new ones
      sim_types (set): Set of sim_types to audit (proprietary_sim_types if None)
    """
    import pykern.pkconfig
    import pykern.pkio
    import sirepo.feature_config
    import sirepo.sim_data
    import sirepo.simulation_db
    import sirepo.util
    import subprocess

    def _add(proprietary_code_dir, sim_type, sim_data_class):
        p = proprietary_code_dir.join(sim_data_class.proprietary_code_tarball())
        with sirepo.simulation_db.tmp_dir(chdir=True, uid=uid) as t:
            d = t.join(p.basename)
            d.mksymlinkto(p, absolute=False)
            subprocess.check_output(
                [
                    'tar',
                    '--extract',
                    '--gunzip',
                    f'--file={d}',
                ],
                stderr=subprocess.STDOUT,
            )
            # lib_dir may not exist: git.radiasoft.org/ops/issues/645
            l = pykern.pkio.mkdir_parent(
                sirepo.simulation_db.simulation_lib_dir(sim_type, uid=uid),
            )
            e = [f.basename for f in pykern.pkio.sorted_glob(l.join('*'))]
            for f in sim_data_class.proprietary_code_lib_file_basenames():
                if force or f not in e:
                    t.join(f).rename(l.join(f))

    s = sirepo.feature_config.cfg().proprietary_sim_types
    if sim_types:
        assert sim_types.issubset(s), \
            f'sim_types={sim_types} not a subset of proprietary_sim_types={s}'
        s = sim_types
    for t in s:
        c = sirepo.sim_data.get_class(t)
        if not c.proprietary_code_tarball():
            return
        d = sirepo.srdb.proprietary_code_dir(t)
        assert d.exists(), \
            f'{d} proprietary_code_dir must exist' \
            + ('; run: sirepo setup_dev' if pykern.pkconfig.channel_in('dev') else '')
        r = UserRole.has_role(
            uid,
            sirepo.auth_role.for_sim_type(t),
        )
        if r:
            _add(d, t, c)
            continue
        # SECURITY: User no longer has access so remove all artifacts
        pykern.pkio.unchecked_remove(sirepo.simulation_db.simulation_dir(t, uid=uid))


def db_filename():
    return sirepo.srdb.root().join(_SQLITE3_BASENAME)


def init():
    def _create_tables(engine):
        b = UserDbBase
        k = set(b.metadata.tables.keys())
        assert k.issubset(set(b.TABLES)), \
            f'sqlalchemy tables={k} not a subset of known tables={b.TABLES}'
        b.metadata.create_all(engine)

    global _engine, DbUpgrade, UserDbBase, UserRegistration, UserRole

    if _engine:
        return
    f = db_filename()
    _migrate_db_file(f)
    _engine = sqlalchemy.create_engine(
        'sqlite:///{}'.format(f),
        # We do our own thread locking so no need to have pysqlite warn us when
        # we access a single connection across threads
        connect_args={'check_same_thread': False},
    )

    @sqlalchemy.ext.declarative.as_declarative()
    class UserDbBase(object):
        STRING_ID = sqlalchemy.String(8)
        STRING_NAME =  sqlalchemy.String(100)
        TABLES = [
            # Order is important. SQLite doesn't allow for foreign key constraints to
            # be added after creation. So, the tables are ordered in the way
            # constraints should be carried out. For example, a user is deleted
            # from auth_email_user_t before user_registration_t.
            'auth_github_user_t',
            'auth_email_user_t',
            'jupyterhub_user_t',
            'user_role_t',
            'user_registration_t',
            'db_upgrade_t',
        ]

        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

        def delete(self):
            with sirepo.util.THREAD_LOCK:
                self._session().delete(self)
                self._session().commit()

        @classmethod
        def delete_user(cls, uid):
            """Delete user from all tables"""
            for t in cls.TABLES:
                m = cls._unchecked_model_from_tablename(t)
                # Exlicit None check because sqlalchemy overrides __bool__ to
                # raise TypeError
                if m is None or 'uid' not in m.columns:
                    continue
                cls.execute(sqlalchemy.delete(m).where(m.c.uid==uid))
            cls._session().commit()

        @classmethod
        def execute(cls, statement):
            cls._session().execute(
                statement.execution_options(synchronize_session='fetch')
            )

        @classmethod
        def delete_all(cls):
            with sirepo.util.THREAD_LOCK:
                cls._session().query(cls).delete()
                cls._session().commit()

        def save(self):
            with sirepo.util.THREAD_LOCK:
                self._session().add(self)
                self._session().commit()

        @classmethod
        def search_all_by(cls, **kwargs):
            with sirepo.util.THREAD_LOCK:
                return cls._session().query(cls).filter_by(**kwargs).all()

        @classmethod
        def search_by(cls, **kwargs):
            with sirepo.util.THREAD_LOCK:
                return cls._session().query(cls).filter_by(**kwargs).first()

        @classmethod
        def search_all_for_column(cls, column, **filter_by):
            with sirepo.util.THREAD_LOCK:
                return [
                    getattr(r, column) for r
                    in cls._session().query(cls).filter_by(**filter_by)
                ]

        @classmethod
        def delete_all_for_column_by_values(cls, column, values):
            with sirepo.util.THREAD_LOCK:
                cls.execute(sqlalchemy.delete(cls).where(
                    getattr(cls, column).in_(values),
                ))
                cls._session().commit()

        @classmethod
        def _session(cls):
            return sirepo.srcontext.get(_SRCONTEXT_SESSION_KEY)

        @classmethod
        def _unchecked_model_from_tablename(cls, tablename):
            for k, v in cls.metadata.tables.items():
                if k == tablename:
                    return v


    class DbUpgrade(UserDbBase):
        __tablename__ = 'db_upgrade_t'
        name = sqlalchemy.Column(UserDbBase.STRING_NAME, primary_key=True)
        created = sqlalchemy.Column(sqlalchemy.DateTime(), nullable=False)


    class UserRegistration(UserDbBase):
        __tablename__ = 'user_registration_t'
        uid = sqlalchemy.Column(UserDbBase.STRING_ID, primary_key=True)
        created = sqlalchemy.Column(sqlalchemy.DateTime(), nullable=False)
        display_name = sqlalchemy.Column(UserDbBase.STRING_NAME)

    class UserRole(UserDbBase):
        __tablename__ = 'user_role_t'
        uid = sqlalchemy.Column(UserDbBase.STRING_ID, primary_key=True)
        role = sqlalchemy.Column(UserDbBase.STRING_NAME, primary_key=True)

        @classmethod
        def all_roles(cls):
            with sirepo.util.THREAD_LOCK:
                return [
                    r[0] for r in cls._session().query(cls.role.distinct()).all()
                ]

        @classmethod
        def add_roles(cls, uid, roles):
            with sirepo.util.THREAD_LOCK:
                for r in roles:
                    UserRole(uid=uid, role=r).save()
                audit_proprietary_lib_files(uid)

        @classmethod
        def delete_roles(cls, uid, roles):
            with sirepo.util.THREAD_LOCK:
                cls.execute(sqlalchemy.delete(cls).where(
                    cls.uid == uid,
                ).where(
                    cls.role.in_(roles),
                ))
                cls._session().commit()
                audit_proprietary_lib_files(uid)

        @classmethod
        def get_roles(cls, uid):
            with sirepo.util.THREAD_LOCK:
                return UserRole.search_all_for_column(
                    'role',
                    uid=uid,
                )


        @classmethod
        def has_role(cls, uid, role):
            with sirepo.util.THREAD_LOCK:
                return bool(cls.search_by(uid=uid, role=role))

        @classmethod
        def uids_of_paid_users(cls):
            return [
                x[0] for x in cls._session().query(cls).with_entities(cls.uid).filter(
                    cls.role.in_(sirepo.auth_role.PAID_USER_ROLES),
                ).distinct().all()
            ]
    _create_tables(_engine)


def init_model(callback):
    with sirepo.util.THREAD_LOCK:
        callback(UserDbBase)
        UserDbBase.metadata.create_all(_engine)


@contextlib.contextmanager
def session():
    init()
    with sirepo.srcontext.create() as c:
        try:
            _create_session(c)
            yield
        finally:
            _destroy_session(c)


@contextlib.contextmanager
def session_and_lock():
    # TODO(e-carlin): Need locking across processes
    # git.radiasoft.org/sirepo/issues/3516
    with session():
        yield

def _create_session(context):
    s = context.get(_SRCONTEXT_SESSION_KEY)
    assert not s, \
        f'existing session={s}'
    context[_SRCONTEXT_SESSION_KEY] = sqlalchemy.orm.Session(bind=_engine)


def _destroy_session(context):
    context.pop(_SRCONTEXT_SESSION_KEY).rollback()


def _migrate_db_file(fn):
    o = fn.new(basename='user.db')
    if not o.exists():
        return
    assert not fn.exists(), \
        'db file collision: old={} and new={} both exist'.format(o, fn)
    try:
        # reduce the race condition between job_supervisor and sirepo starting
        x = o + '-migrating'
        if x.exists():
            # again, reduce race condition
            return
        o.rename(x)

        import sqlite3

        c = sqlite3.connect(str(x))
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
    x.rename(o + '-migrated')
    pkdlog('migrated user.db to auth.db')
