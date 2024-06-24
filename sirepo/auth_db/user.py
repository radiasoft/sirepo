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

    def all_roles(self):
        cls = self.__class__
        return [r[0] for r in self.query().distinct(cls.role).all()]

    def add_roles(self, roles, expiration=None):
        from sirepo import sim_data

        u = self.logged_in_user()
        for r in roles:
            try:
                # Check here, because sqlite doesn't through IntegrityErrors
                # at the point of the new() operation.
                if not self.has_role(r, uid=u):
                    self.new(uid=u, role=r, expiration=expiration).save()
            except sqlalchemy.exc.IntegrityError:
                # role already exists
                pass
        sim_data.audit_proprietary_lib_files(qcall=self.auth_db.qcall)

    def add_role_or_update_expiration(self, role, expiration):
        if not self.has_role(role):
            self.add_roles(roles=[role], expiration=expiration)
            return
        r = self.search_by(uid=self.logged_in_user(), role=role)
        r.expiration = expiration
        r.save()

    def delete_roles(self, roles, uid=None):
        from sirepo import sim_data

        cls = self.__class__
        self.auth_db.execute(
            sqlalchemy.delete(cls)
            .where(
                cls.uid == (uid or self.logged_in_user()),
            )
            .where(
                cls.role.in_(roles),
            )
        )
        sim_data.audit_proprietary_lib_files(qcall=self.auth_db.qcall)

    def get_roles(self):
        return self.search_all_for_column("role", uid=self.logged_in_user())

    def has_role(self, role, uid=None):
        return bool(
            self.unchecked_search_by(uid=uid or self.logged_in_user(), role=role)
        )

    def is_expired(self, role):
        u = self.logged_in_user()
        assert self.has_role(role=role), f"No role for uid={u} and role={role}"
        r = self.search_by(uid=u, role=role)
        if not r.expiration:
            # Roles with no expiration can't expire
            return False
        return r.expiration < sirepo.srtime.utc_now()

    def uids_of_paid_users(self):
        return self.uids_with_roles(sirepo.auth_role.PAID_USER_ROLES)

    def uids_with_roles(self, roles):
        a = sirepo.auth_role.get_all()
        assert not (d := set(roles) - set(a)), f"roles={d} unknown all_roles={a}"
        cls = self.__class__
        return [
            x[0]
            for x in self.query()
            .with_entities(cls.uid)
            .filter(
                cls.role.in_(roles),
            )
            .distinct()
            .all()
        ]


class UserRoleModeration(sirepo.auth_db.UserDbBase):
    __tablename__ = "user_role_moderation_t"
    uid = sqlalchemy.Column(sirepo.auth_db.STRING_ID, primary_key=True)
    role = sqlalchemy.Column(sirepo.auth_db.STRING_NAME, primary_key=True)
    status = sqlalchemy.Column(sirepo.auth_db.STRING_NAME, nullable=False)
    moderator_uid = sqlalchemy.Column(sirepo.auth_db.STRING_ID)
    last_updated = sqlalchemy.Column(
        sqlalchemy.DateTime(),
        server_default=sqlalchemy.sql.func.now(),
        onupdate=sqlalchemy.sql.func.now(),
        nullable=False,
    )

    def get_moderation_request_rows(self):
        cls = self.__class__
        e = self.auth_db.model("AuthEmailUser").__class__
        q = (
            self.auth_db.query(e)
            .with_entities(
                e.user_name.label("email"),
                *cls.__table__.columns,
            )
            .filter(
                e.uid == cls.uid,
                sqlalchemy.sql.expression.or_(
                    cls.status == "pending", cls.status == "clarify"
                ),
            )
            .all()
        )
        return [PKDict(zip(r.keys(), r)) for r in q]

    def get_status(self, role, uid=None):
        s = self.unchecked_search_by(uid=uid or self.logged_in_user(), role=role)
        if not s:
            return None
        return sirepo.auth_role.ModerationStatus.check(s.status)

    def set_status(self, role, status, moderator_uid):
        s = self.search_by(uid=self.logged_in_user(), role=role)
        s.status = sirepo.auth_role.ModerationStatus.check(status)
        if moderator_uid:
            s.moderator_uid = moderator_uid
        s.save()
