# -*- coding: utf-8 -*-
"""?

:copyright: Copyright (c) 2022 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
import sirepo.auth_db
import sirepo.auth_role
import sirepo.srtime
import sirepo.util
import sqlalchemy


class UserRegistration(sirepo.auth_db.UserDbBase):
    __tablename__ = "user_registration_t"
    uid = sqlalchemy.Column(sirepo.auth_db.STRING_ID, primary_key=True)
    created = sqlalchemy.Column(sqlalchemy.DateTime(), nullable=False)
    display_name = sqlalchemy.Column(sirepo.auth_db.STRING_NAME)


class UserRole(sirepo.auth_db.UserDbBase):
    __tablename__ = "user_role_t"
    uid = sqlalchemy.Column(sirepo.auth_db.STRING_ID, primary_key=True)
    role = sqlalchemy.Column(sirepo.auth_db.STRING_NAME, primary_key=True)
    expiration = sqlalchemy.Column(sqlalchemy.DateTime())

    @classmethod
    def all_roles(cls):
        with sirepo.util.THREAD_LOCK:
            return [r[0] for r in cls._session().query(cls.role.distinct()).all()]

    @classmethod
    def add_roles(cls, qcall, roles, expiration=None):
        with sirepo.util.THREAD_LOCK:
            u = qcall.auth.logged_in_user()
            for r in roles:
                try:
                    UserRole(
                        uid=u,
                        role=r,
                        expiration=expiration,
                    ).save()
                except sqlalchemy.exc.IntegrityError:
                    pass
            sirepo.auth_db.audit_proprietary_lib_files(qcall=qcall)

    @classmethod
    def add_role_or_update_expiration(cls, qcall, role, expiration):
        with sirepo.util.THREAD_LOCK:
            if not cls.has_role(qcall, role):
                cls.add_roles(qcall=qcall, roles=[role], expiration=expiration)
                return
            r = cls.search_by(uid=qcall.auth.logged_in_user(), role=role)
            r.expiration = expiration
            r.save()

    @classmethod
    def delete_roles(cls, qcall, roles):
        with sirepo.util.THREAD_LOCK:
            cls.execute(
                sqlalchemy.delete(cls)
                .where(
                    cls.uid == qcall.auth.logged_in_user(),
                )
                .where(
                    cls.role.in_(roles),
                )
            )
            cls._session().commit()
            sirepo.auth_db.audit_proprietary_lib_files(qcall=qcall)

    @classmethod
    def get_roles(cls, qcall):
        with sirepo.util.THREAD_LOCK:
            return UserRole.search_all_for_column(
                "role",
                uid=qcall.auth.logged_in_user(),
            )

    @classmethod
    def has_role(cls, qcall, role):
        with sirepo.util.THREAD_LOCK:
            return bool(cls.search_by(uid=qcall.auth.logged_in_user(), role=role))

    @classmethod
    def is_expired(cls, qcall, role):
        with sirepo.util.THREAD_LOCK:
            u = qcall.auth.logged_in_user()
            assert cls.has_role(
                qcall=qcall, role=role
            ), f"No role for uid={u} and role={role}"
            r = cls.search_by(uid=u, role=role)
            if not r.expiration:
                # Roles with no expiration can't expire
                return False
            return r.expiration < sirepo.srtime.utc_now()

    @classmethod
    def uids_of_paid_users(cls):
        return [
            x[0]
            for x in cls._session()
            .query(cls)
            .with_entities(cls.uid)
            .filter(
                cls.role.in_(sirepo.auth_role.PAID_USER_ROLES),
            )
            .distinct()
            .all()
        ]


class UserRoleInvite(sirepo.auth_db.UserDbBase):
    __tablename__ = "user_role_invite_t"
    uid = sqlalchemy.Column(sirepo.auth_db.STRING_ID, primary_key=True)
    role = sqlalchemy.Column(sirepo.auth_db.STRING_NAME, primary_key=True)
    status = sqlalchemy.Column(sirepo.auth_db.STRING_NAME, nullable=False)
    token = sqlalchemy.Column(sirepo.auth_db.STRING_NAME, nullable=False, unique=True)
    moderator_uid = sqlalchemy.Column(sirepo.auth_db.STRING_ID)
    last_updated = sqlalchemy.Column(
        sqlalchemy.DateTime(),
        server_default=sqlalchemy.sql.func.now(),
        onupdate=sqlalchemy.sql.func.now(),
        nullable=False,
    )

    @classmethod
    def get_moderation_request_rows(cls, qcall):
        from sirepo import auth

        t = qcall.auth.get_module("email").UserModel
        with sirepo.util.THREAD_LOCK:
            q = (
                cls._session()
                .query(t, cls)
                .with_entities(
                    t.user_name.label("email"),
                    *cls.__table__.columns,
                )
                .filter(
                    t.uid == cls.uid,
                    sqlalchemy.sql.expression.or_(
                        cls.status == "pending", cls.status == "clarify"
                    ),
                )
                .all()
            )
        return [PKDict(zip(r.keys(), r)) for r in q]

    @classmethod
    def get_status(cls, qcall, role):
        with sirepo.util.THREAD_LOCK:
            s = cls.search_by(uid=qcall.auth.logged_in_user(), role=role)
            if not s:
                return None
            return sirepo.auth_role.ModerationStatus.check(s.status)

    @classmethod
    def set_status(cls, qcall, role, status, moderator_uid):
        with sirepo.util.THREAD_LOCK:
            s = cls.search_by(uid=qcall.auth.logged_in_user(), role=role)
            s.status = sirepo.auth_role.ModerationStatus.check(status)
            if moderator_uid:
                s.moderator_uid = moderator_uid
            s.save()
