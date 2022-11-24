# -*- coding: utf-8 -*-
"""Auth database

:copyright: Copyright (c) 2018-2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp
import contextlib
import importlib
import inspect
import pykern.pkconfig
import pykern.pkio
import pykern.pkinspect
import sirepo.auth_role
import sirepo.feature_config
import sirepo.quest
import sirepo.srdb
import sqlalchemy
import sqlalchemy.ext.declarative
import sqlalchemy.orm
import sqlalchemy.sql.expression
import subprocess


#: sqlite file located in sirepo_db_dir
_SQLITE3_BASENAME = "auth.db"

#: SQLAlchemy database engine
_engine = None

STRING_ID = sqlalchemy.String(8)
STRING_NAME = sqlalchemy.String(100)

_models = None


@sqlalchemy.ext.declarative.as_declarative()
class UserDbBase:
    def all(self):
        return self.auth_db.query(self).all()

    def as_pkdict(self):
        return PKDict({c: getattr(self, c) for c in self.column_names()})

    def column_names(self):
        return self.__table__.columns.keys()

    def delete(self):
        self.auth_db.session().delete(self)

    def delete_all(self):
        self.auth_db.query(self).delete()

    def delete_all_for_column_by_values(self, column, values):
        cls = self.__class__
        self.auth_db.execute(
            sqlalchemy.delete(cls).where(
                getattr(cls, column).in_(values),
            )
        )

    def save(self):
        self.auth_db.session().add(self)

    def search_by(self, **kwargs):
        return self.auth_db.query(self).filter_by(**kwargs).first()

    def search_all_for_column(self, column, **filter_by):
        return [
            getattr(r, column)
            for r in self.auth_db.query(self).filter_by(**filter_by)
        ]


def db_filename():
    return sirepo.srdb.root().join(_SQLITE3_BASENAME)


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

    def _export_models():
        m = pykern.pkinspect.this_module()
        res = PKDict()
        for n, x in _classes().items():
            assert not hasattr(m, n), f"class={n} already exists"
            setattr(m, n, x.cls)
            res[n] = x.cls
        return res

    global _engine, _models

    if _engine:
        return
    _models = _export_models()
    _engine = sqlalchemy.create_engine(
        f"sqlite:///{db_filename()}",
        # We ensure single threaded access through locking
        connect_args={"check_same_thread": False},
    )


def init_quest(qcall):
    qcall.attr_set("auth_db", _AuthDb(qcall=qcall))


class _AuthDb(sirepo.quest.Attr):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._orm_session = None
        for

    def add_column_if_not_exists(self, model, column, column_type):
        """Must not be called with user data"""
        column_type = column_type.upper()
        t = model.__table__.name
        r = self._execute_sql(f"PRAGMA table_info({t})")
        for c in r.all():
            if not c[1] == column:
                continue
            assert c[2] == column_type, (
                f"unexpected column={c} when adding column={column} of",
                f" type={column_type} to table={t}",
            )
            return
        self._execute_sql(
            "ALTER TABLE :t ADD :col :ct",
            t=t,
            col=column,
            ct=column_type,
        )

    def all_uids(self):
        return UserRegistration.search_all_for_column(qcall=self.qcall, "uid")

    def commit(self):
        self._commit_or_rollback(commit=True)

    def create_or_upgrade(self):
        from sirepo import db_upgrade

        self.metadata().create_all(bind=_engine)
        db_upgrade.do_all(qcall=self.qcall)

    def delete_user(self, uid):
        """Delete user from all models"""
        for m in _models.values():
            # Exlicit None check because sqlalchemy overrides __bool__ to
            # raise TypeError
            if m is None or "uid" not in m.__table__.columns:
                continue
            self.execute(sqlalchemy.delete(m).where(m.uid == uid))

    def destroy(self, commit=False, **kwargs):
        self._commit_or_rollback(commit=commit)

    def execute(self, statement):
        return self.session().execute(
            statement.execution_options(synchronize_session="fetch")
        )

    def metadata(self):
        return UserDbBase.metadata

    def model(self, name, **kwargs):
        x = _models[name](**kwargs)
        x.auth_db = self
        return x

    def query(self, model):
        return self.session().query(model)

    def rename_table(self, old, new):
        self._execute_sql(
            f"ALTER TABLE :old RENAME TO :new",
            old=old,
            new=new,
        )

    def session(self):
        if self._orm_session is None:
            # New in sqlalchemy 2.0 autobegin, which we should set to False
            self._orm_session = sqlalchemy.orm.Session(bind=_engine)
            self._orm_session.begin()
        return self._orm_session

    def _commit_or_rollback(self, commit):
        if _orm_session is None:
            return
        s = self._orm_session
        self._orm_session = None
        if commit:
            s.commit()
        else:
            s.rollback()
        s.close()

    def _execute_sql(self, text, **kwargs):
        return self.execute(sqlalchemy.text(text + ";"), **kwargs)
