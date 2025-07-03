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

    def add_plan(self, role, uid, expiration=None):
        # TODO(robnagler) always trust stripe?
        # Assert role and probably need sanity check...
        e = sirepo.util.plan_role_expiration(role)
        if expiration:
            e = expiration
        self.add_roles([role], uid, expiration=e)

    def add_roles(self, roles, uid, expiration=None):
        """Add roles or update expiration"""
        from sirepo import sim_data

        for r in roles:
            if len(r) <= 1:
                raise AssertionError(f"no single letter role={r}")
            # Check here, because sqlite doesn't throw IntegrityErrors
            # at the point of the new() operation.
            if x := self._has_role(r, uid):
                x.expiration = expiration
            try:
                # The save() is probably what throws the integrity constraint
                self.new(uid=uid, role=r, expiration=expiration).save()
            except sqlalchemy.exc.IntegrityError:
                self.set_role_expiration(r, uid, expiration)
        sim_data.audit_proprietary_lib_files(qcall=self.auth_db.qcall, uid=uid)

    def delete_roles(self, roles, uid):
        from sirepo import sim_data

        cls = self.__class__
        self.auth_db.execute(
            sqlalchemy.delete(cls)
            .where(
                cls.uid == uid,
            )
            .where(
                cls.role.in_(roles),
            )
        )
        sim_data.audit_proprietary_lib_files(qcall=self.auth_db.qcall, uid=uid)

    def expire_role(self, role, uid):
        self.set_role_expiration(role, uid, sirepo.srtime.utc_now())

    def get_roles(self, uid):
        return self.search_all_for_column("role", uid=uid)

    def get_roles_and_expiration(self, uid):
        return [
            PKDict(role=r.role, expiration=r.expiration)
            for r in self.query().filter_by(uid=uid)
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

    def has_active_role(self, role, uid):
        r = self._has_role(role, uid)
        return r and not self._is_expired_role(r)

    def has_expired_role(self, role, uid):
        r = self._has_role(role, uid)
        return r and self._is_expired_role(r)

    def set_role_expiration(self, role, uid, expiration):
        r = self.search_by(uid=uid, role=role)
        r.expiration = expiration
        r.save()

    def uids_of_paid_users(self):
        return self.uids_with_roles(sirepo.auth_role.PLAN_ROLES_PAID)

    def uids_with_roles(self, roles):
        for r in roles:
            sirepo.auth_role.check(r)
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

    def _has_role(self, role, uid):
        return self.unchecked_search_by(uid=uid, role=role)

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

    def get_status(self, role, uid):
        s = self.unchecked_search_by(uid=uid, role=role)
        if not s:
            return None
        return sirepo.auth_role.ModerationStatus.check(s.status)

    def set_status(self, role, uid, status, moderator_uid):
        s = self.search_by(uid=uid, role=role)
        s.status = sirepo.auth_role.ModerationStatus.check(status)
        if moderator_uid:
            s.moderator_uid = moderator_uid
        s.save()
