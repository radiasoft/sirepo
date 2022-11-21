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
import sirepo.srtime
import sirepo.util
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
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

    @classmethod
    def add_column_if_not_exists(cls, table, column, column_type):
        """Must not be called with user data"""
        column_type = column_type.upper()
        t = table.__table__.name
        r = cls._execute_sql(f"PRAGMA table_info({t})")
        for c in r.all():
            if not c[1] == column:
                continue
            assert c[2] == column_type, (
                f"unexpected column={c} when adding column={column} of",
                f" type={column_type} to table={table}",
            )
            return
        cls._execute_sql("ALTER TABLE :t ADD :col :ct", t=t, col=column, ct=column_type)
        cls._session().commit()

    @classmethod
    def all(cls):
        with sirepo.util.THREAD_LOCK:
            return cls._session().query(cls).all()

    def as_pkdict(self):
        return PKDict({c: getattr(self, c) for c in self.column_names()})

    @classmethod
    def column_names(cls):
        return cls.__table__.columns.keys()

    def delete(self):
        with sirepo.util.THREAD_LOCK:
            self._session().delete(self)
            self._session().commit()

    @classmethod
    def delete_all(cls):
        with sirepo.util.THREAD_LOCK:
            cls._session().query(cls).delete()
            cls._session().commit()

    @classmethod
    def delete_all_for_column_by_values(cls, column, values):
        with sirepo.util.THREAD_LOCK:
            cls.execute(
                sqlalchemy.delete(cls).where(
                    getattr(cls, column).in_(values),
                )
            )
            cls._session().commit()

    @classmethod
    def delete_user(cls, uid):
        """Delete user from all models"""
        for m in _models:
            # Exlicit None check because sqlalchemy overrides __bool__ to
            # raise TypeError
            if m is None or "uid" not in m.__table__.columns:
                continue
            cls.execute(sqlalchemy.delete(m).where(m.uid == uid))
        cls._session().commit()

    @classmethod
    def execute(cls, statement):
        return cls._session().execute(
            statement.execution_options(synchronize_session="fetch")
        )

    @classmethod
    def rename_table(cls, old, new):
        cls._execute_sql(f"ALTER TABLE :old RENAME TO :new", old=old, new=new)
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
                getattr(r, column)
                for r in cls._session().query(cls).filter_by(**filter_by)
            ]

    @classmethod
    def _execute_sql(cls, text, **kwargs):
        return cls.execute(sqlalchemy.text(text + ";"), **kwargs)

    @classmethod
    def _session(cls):
        return sirepo.quest.hack_current().auth_db._orm_session


def all_uids(qcall):
    return UserRegistration.search_all_for_column("uid")


def audit_proprietary_lib_files(qcall, force=False, sim_types=None):
    """Add/removes proprietary files based on a user's roles

    For example, add the Flash tarball if user has the flash role.

    Args:
      qcall (quest.API): logged in user
      force (bool): Overwrite existing lib files with the same name as new ones
      sim_types (set): Set of sim_types to audit (proprietary_sim_types if None)
    """
    from sirepo import sim_data, simulation_db

    def _add(proprietary_code_dir, sim_type, sim_data_class):
        p = proprietary_code_dir.join(sim_data_class.proprietary_code_tarball())
        with simulation_db.tmp_dir(chdir=True, qcall=qcall) as t:
            d = t.join(p.basename)
            d.mksymlinkto(p, absolute=False)
            subprocess.check_output(
                [
                    "tar",
                    "--extract",
                    "--gunzip",
                    f"--file={d}",
                ],
                stderr=subprocess.STDOUT,
            )
            # lib_dir may not exist: git.radiasoft.org/ops/issues/645
            l = pykern.pkio.mkdir_parent(
                simulation_db.simulation_lib_dir(sim_type, qcall=qcall),
            )
            e = [f.basename for f in pykern.pkio.sorted_glob(l.join("*"))]
            for f in sim_data_class.proprietary_code_lib_file_basenames():
                if force or f not in e:
                    t.join(f).rename(l.join(f))

    s = sirepo.feature_config.proprietary_sim_types()
    if sim_types:
        assert sim_types.issubset(
            s
        ), f"sim_types={sim_types} not a subset of proprietary_sim_types={s}"
        s = sim_types
    u = qcall.auth.logged_in_user()
    for t in s:
        c = sim_data.get_class(t)
        if not c.proprietary_code_tarball():
            continue
        d = sirepo.srdb.proprietary_code_dir(t)
        assert d.exists(), f"{d} proprietary_code_dir must exist" + (
            "; run: sirepo setup_dev" if pykern.pkconfig.channel_in("dev") else ""
        )
        r = UserRole.has_role(
            qcall=qcall,
            role=sirepo.auth_role.for_sim_type(t),
        )
        if r:
            _add(d, t, c)
            continue
        # SECURITY: User no longer has access so remove all artifacts
        pykern.pkio.unchecked_remove(simulation_db.simulation_dir(t, qcall=qcall))


def create_or_upgrade(qcall):
    from sirepo import db_upgrade

    UserDbBase.metadata.create_all(bind=_engine)
    db_upgrade.do_all(qcall)


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
        res = []
        for n, x in _classes().items():
            assert not hasattr(m, n), f"class={n} already exists"
            setattr(m, n, x.cls)
            res.append(x.cls)
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
    qcall.attr_set("auth_db", _AuthDb())


@contextlib.contextmanager
def session():
    qcall = sirepo.quest.API()
    try:
        init_quest(qcall)
        yield
    finally:
        qcall.destroy()


@contextlib.contextmanager
def session_and_lock():
    # TODO(e-carlin): Need locking across processes
    # git.radiasoft.org/sirepo/issues/3516
    with session():
        yield


class _AuthDb(sirepo.quest.Attr):
    def __init__(self):
        super().__init__()
        self._orm_session = sqlalchemy.orm.Session(bind=_engine)

    def destroy(self):
        self._orm_session.rollback()
