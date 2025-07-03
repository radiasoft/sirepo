"""CRUD operations for user roles

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp
from sirepo.pkcli import admin
import contextlib
import datetime
import pykern.pkcli
import sirepo.auth_role
import sirepo.quest


def add(uid_or_email, *roles, expiration=None):
    """Assign roles to a user.
    Args:
        uid_or_email (str): Uid or email of the user
        *roles (str): The roles to assign to the user
        expiration (int): Days until expiration
    """
    with _parse_args(uid_or_email, roles, expiration) as a:
        a.qcall.auth_db.model("UserRole").add_roles(
            a.roles,
            uid=a.uid,
            expiration=a.expiration,
        )


def add_plan(uid_or_email, plan, expiration=None):
    """Assign a plan to a user.
    Args:
        uid_or_email (str): Uid or email of the user
        plan (str): The plan to assign to the user
        expiration (int): Days until expiration
    """
    with _parse_args(uid_or_email, [plan], expiration) as a:
        a.qcall.auth_db.model("UserRole").add_plan(a.roles[0], a.uid, a.expiration)


def add_roles(*args, **kwargs):
    """DEPRECATED: Use add"""
    add(*args, **kwargs)


def delete(uid_or_email, *roles):
    """Remove roles assigned to user
    Args:
        uid_or_email (str): Uid or email of the user
        *roles (args): The roles to delete
    """

    with _parse_args(uid_or_email, roles) as a:
        a.qcall.auth_db.model("UserRole").delete_roles(a.roles, a.uid)


def delete_roles(*args, **kwargs):
    """DEPRECATED: Use delete"""
    delete(*args, **kwargs)


def disable_user(uid_or_email, moderator):
    """Remove role user
    Args:
        uid_or_email (str): Uid or email of the user
        moderator (str): Uid or email
    """
    with _parse_args(uid_or_email) as a:
        a.qcall.auth_db.model("UserRole").delete_roles(
            [sirepo.auth_role.ROLE_USER], a.uid
        )
        a.qcall.auth_db.model(
            "UserRoleModeration",
            uid=a.uid,
            role=sirepo.auth_role.ROLE_USER,
            status=sirepo.auth_role.ModerationStatus.DENY,
            moderator_uid=_uid(a.qcall, moderator),
        ).save()


def list(uid_or_email):
    """List all roles assigned to a user
    Args:
        uid_or_email (str): Uid or email of the user
    """

    with _parse_args(uid_or_email) as a:
        return a.qcall.auth_db.model("UserRole").get_roles(a.uid)


def list_with_expiration(uid_or_email):
    """List all roles assigned to a user with their expiration.
    Args:
        uid_or_email (str): Uid or email of the user
    """

    with _parse_args(uid_or_email) as a:
        return a.qcall.auth_db.model("UserRole").get_roles_and_expiration(a.uid)


def list_roles(*args):
    """DEPRECATED: Use list"""
    return list(*args)


def _uid(qcall, uid_or_email):
    rv = qcall.auth.unchecked_get_user(uid_or_email)
    if not rv:
        pykern.pkcli.command_error("uid_or_email={} not found", uid_or_email)
    return rv


# TODO(e-carlin): This only works for email auth or using a uid
# doesn't work for other auth methods
@contextlib.contextmanager
def _parse_args(uid_or_email, roles=None, expiration=None):
    def _expiration():
        return (
            None
            if expiration is None
            else (datetime.datetime.utcnow() + datetime.timedelta(days=int(expiration)))
        )

    rv = PKDict()
    with sirepo.quest.start() as rv.qcall:
        rv.uid = _uid(rv.qcall, uid_or_email)
        if roles is not None:
            if not roles:
                pykern.pkcli.command_error("must supply at least one role")
            for r in roles:
                sirepo.auth_role.check(r)
            rv.roles = roles
        rv.expiration = _expiration()
        yield rv
