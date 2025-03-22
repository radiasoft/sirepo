"""Auth database

:copyright: Copyright (c) 2018-2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp
import functools
import importlib
import inspect
import pykern.pkconfig
import pykern.pkinspect
import sirepo.quest
import sirepo.srdb
import sirepo.util
import sqlalchemy
import sqlalchemy.ext.declarative
import sqlalchemy.orm
import sqlalchemy.sql.expression
import re


#: sqlite file located in sirepo_db_dir
_SQLITE3_BASENAME = "auth.db"

#: SQLAlchemy database engine
_engine = None

_UNIQUE_ID_LEN = 8
STRING_ID = sqlalchemy.String(_UNIQUE_ID_LEN)
STRING_NAME = sqlalchemy.String(100)
_PRIMARY_KEY_PREFIX_SEP = "_"
_PRIMARY_KEY_PREFIX_LEN = 3
_PRIMARY_KEY_PREFIX_RE = re.compile("^[a-z]{3}$")
_PRIMARY_KEY_LEN = (
    _PRIMARY_KEY_PREFIX_LEN + len(_PRIMARY_KEY_PREFIX_SEP) + _UNIQUE_ID_LEN
)

_models = None

_created = False


@sqlalchemy.ext.declarative.as_declarative()
class UserDbBase:
    def as_pkdict(self):
        return PKDict({c: getattr(self, c) for c in self.column_names()})

    def column_names(self):
        return self.__table__.columns.keys()

    def delete(self):
        self.auth_db.session().delete(self)

    def delete_all(self):
        self.query().delete()

    def delete_all_for_column_by_values(self, column, values):
        cls = self.__class__
        self.auth_db.execute(
            sqlalchemy.delete(cls).where(
                getattr(cls, column).in_(values),
            )
        )

    def logged_in_user(self):
        return self.auth_db.qcall.auth.logged_in_user()

    def new(self, **fields):
        return self.auth_db.model(self.__class__.__name__, **fields)

    def query(self, *other):
        return self.auth_db.query(self, *other)

    def save(self):
        self.auth_db.session().add(self)

    def search_by(self, **filter_by):
        return self._new(self.query().filter_by(**filter_by).one())

    def search_all_for_column(self, column, **filter_by):
        return [getattr(r, column) for r in self.query().filter_by(**filter_by)]

    def unchecked_search_all(self, **filter_by):
        return self.query().filter_by(**filter_by).all()

    def unchecked_search_by(self, **filter_by):
        return self._new(self.query().filter_by(**filter_by).one_or_none())

    def _new(self, result):
        if result is None:
            return result
        result.auth_db = self.auth_db
        return result


def db_filename():
    return sirepo.srdb.root().join(_SQLITE3_BASENAME)


def get_class(name):
    return _models[name].cls


def init_module():
    def _classes():
        res = PKDict()
        p = pykern.pkinspect.this_module().__name__
        for x in pykern.pkinspect.package_module_names(p):
            q = pykern.pkinspect.module_name_join((p, x))
            m = importlib.import_module(q)
            for n, c in inspect.getmembers(
                m,
                predicate=lambda z: inspect.isclass(z) and issubclass(z, UserDbBase),
            ):
                if n in res:
                    raise AssertionError(
                        f"class={n} in module={q} also found in module={res[n].module_name}",
                    )
                res[n] = PKDict(module_name=q, cls=c)
        return res

    global _cfg, _engine, _models

    if _engine:
        return
    _cfg = pykern.pkconfig.init(
        sqlite_timeout=(20, int, "sqlite connection timeout"),
    )
    _models = _classes()
    _engine = sqlalchemy.create_engine(
        f"sqlite:///{db_filename()}",
        # We ensure single threaded access by not sharing connections.
        # TODO(robnagler) set pool_class=NullPool with sqlalchemy 2.0
        connect_args={
            "check_same_thread": False,
            "timeout": _cfg.sqlite_timeout,
        },
        # echo=True,
        # echo_pool=True,
    )


def init_quest(qcall):
    _AuthDb(qcall=qcall)


def primary_key_column(prefix):
    def _gen(prefix_and_sep):
        return prefix_and_sep + sirepo.util.random_base62(_UNIQUE_ID_LEN)

    if not _PRIMARY_KEY_PREFIX_RE.search(prefix):
        raise AssertionError(f"prefix={prefix} must match={_PRIMARY_KEY_PREFIX_RE}")
    return sqlalchemy.Column(
        sqlalchemy.String(_PRIMARY_KEY_LEN),
        primary_key=True,
        default=functools.partial(_gen, prefix + _PRIMARY_KEY_PREFIX_SEP),
    )


class _AuthDb(sirepo.quest.Attr):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._orm_session = None

    def add_column_if_not_exists(self, model, column, column_type):
        """Must not be called with user data"""
        column_type = column_type.upper()
        t = model.__table__.name
        r = self.execute_sql(f"PRAGMA table_info({t})")
        for c in r.all():
            if not c[1] == column:
                continue
            assert c[2] == column_type, (
                f"unexpected column={c} when adding column={column} of",
                f" type={column_type} to table={t}",
            )
            return
        self.execute_sql(f"ALTER TABLE {t} ADD {column} {column_type}")

    def all_uids(self):
        return list(self.model("UserRegistration").search_all_for_column("uid"))

    def commit(self):
        self._commit_or_rollback(commit=True)

    def create_or_upgrade(self):
        global _created
        if _created:
            return
        _created = True
        from sirepo import db_upgrade

        self.metadata().create_all(bind=_engine)
        db_upgrade.do_all(qcall=self.qcall)

    def delete_user(self, uid):
        """Delete user from all models"""
        for m in _models.values():
            c = m.cls
            if "uid" not in c.__table__.columns:
                continue
            self.execute(sqlalchemy.delete(c).where(c.uid == uid))

    def destroy(self, commit=False, **kwargs):
        self._commit_or_rollback(commit=commit)

    def drop_table(self, old):
        self.execute_sql(f"DROP TABLE IF EXISTS {old}")

    def execute(self, statement):
        return self.session().execute(
            statement.execution_options(synchronize_session="fetch")
        )

    def execute_sql(self, text, params=None):
        q = sqlalchemy.text(text + ";")
        if params:
            q = q.bindparams(**params)
        return self.execute(q)

    def metadata(self):
        return UserDbBase.metadata

    def model(self, class_name_, **fields):
        x = get_class(class_name_)(**fields)
        x.auth_db = self
        return x

    def query(self, *models):
        def _class(obj):
            if isinstance(obj, UserDbBase):
                return obj.__class__
            if isinstance(obj, str):
                return get_class(obj)
            if inspect.isclass(obj) and issubclass(obj, UserDbBase):
                return obj
            raise AssertionError(f"invalid object={obj}")

        return self.session().query(*(_class(m) for m in models))

    def rename_table(self, old, new):
        self.execute_sql(f"ALTER TABLE {old} RENAME TO {new}")

    def session(self):
        if self._orm_session is None:
            # New in sqlalchemy 2.0 autobegin, which we should set to False
            self._orm_session = sqlalchemy.orm.Session(bind=_engine)
            self._orm_session.begin()
        return self._orm_session

    def table_exists(self, table_name):
        return table_name in sqlalchemy.inspect(_engine).get_table_names()

    def _commit_or_rollback(self, commit):
        if self._orm_session is None:
            return
        s = self._orm_session
        self._orm_session = None
        if commit:
            s.commit()
        else:
            s.rollback()
        s.close()

    def init_quest_for_child(self, *args, **kwargs):
        # TODO(robnagler): Consider nested transactions
        #
        # For now, we have to commit because we don't have nesting.
        # Commit at the end of this child-qcall which shares auth_db.
        # auth_db is robust here since it dynamically creates sessions.
        self.commit()
        return super().init_quest_for_child(*args, **kwargs)
