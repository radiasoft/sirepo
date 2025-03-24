"""auth database models for user roles.

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

    def add_roles(self, roles, expiration=None, uid=None):
        from sirepo import sim_data

        u = uid or self.logged_in_user()
        for r in roles:
            try:
                # Check here, because sqlite doesn't throw IntegrityErrors
                # at the point of the new() operation.
                if not self._has_role(r, uid=u):
                    self.new(uid=u, role=r, expiration=expiration).save()
            except sqlalchemy.exc.IntegrityError:
                # role already exists
                pass
        sim_data.audit_proprietary_lib_files(qcall=self.auth_db.qcall)

    def add_role_or_update_expiration(self, role, expiration):
        if not self._has_role(role):
            self.add_roles(roles=[role], expiration=expiration)
            return
        self.set_role_expiration(role, expiration)

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

    def expire_role(self, role, uid=None):
        self.set_role_expiration(role, sirepo.srtime.utc_now(), uid=uid)

    def get_roles(self):
        return self.search_all_for_column("role", uid=self.logged_in_user())

    def get_roles_and_expiration(self):
        return [
            PKDict(role=r.role, expiration=r.expiration)
            for r in self.query().filter_by(uid=self.logged_in_user())
        ]

    def has_active_plan(self, uid):
        cls = self.__class__
        return bool(
            self.query()
            .filter(
                cls.role.in_(sirepo.auth_role.PLAN_ROLES),
                cls.uid == uid,
                sqlalchemy.or_(
                    cls.expiration.is_(None),
                    cls.expiration > sirepo.srtime.utc_now(),
                ),
            )
            .first()
        )

    def has_active_role(self, role, uid=None):
        r = self._has_role(role, uid=uid)
        return r and not self._is_expired_role(r)

    def has_expired_role(self, role, uid=None):
        r = self._has_role(role, uid=uid)
        return r and self._is_expired_role(r)

    def set_role_expiration(self, role, expiration, uid=None):
        r = self.search_by(uid=uid or self.logged_in_user(), role=role)
        r.expiration = expiration
        r.save()

    def uids_of_paid_users(self):
        return self.uids_with_roles(sirepo.auth_role.PLAN_ROLES_PAID)

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

    def _has_role(self, role, uid=None):
        return self.unchecked_search_by(uid=uid or self.logged_in_user(), role=role)

    def _is_expired_role(self, role_record):
        return (
            role_record.expiration and role_record.expiration < sirepo.srtime.utc_now()
        )


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
