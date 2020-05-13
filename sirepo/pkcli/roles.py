# -*- coding: utf-8 -*-
u"""CRUD operations for user roles

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp
from sirepo.pkcli import admin
import sirepo.auth
import sirepo.auth.email
import sirepo.auth_db
import sirepo.server


def add_roles(uid_or_email, *args):
    """Assign roles to a user
    Args:
        uid_or_email (str): Uid or email of the user
        *args: The roles to assign to the user
    """
    u = _check_uid_or_email_and_roles(uid_or_email, args)
    sirepo.auth_db.UserRole.add_roles(u, args)
    admin.audit_proprietary_lib_files(u)



def delete_roles(uid_or_email, *args):
    """Remove roles assigned to user
    Args:
        uid_or_email (str): Uid or email of the user
        *args: The roles to delete
    """
    u = _check_uid_or_email_and_roles(uid_or_email, args)
    sirepo.auth_db.UserRole.delete_roles(u, args)
    admin.audit_proprietary_lib_files(u)


def list_roles(uid_or_email):
    """List all roles assigned to a user
    Args:
        uid_or_email (str): Uid or email of the user
    """
    u = _check_uid_or_email_and_roles(uid_or_email, [])
    return sirepo.auth_db.UserRole.search_all_for_column('role', uid=u)


def _check_uid_or_email_and_roles(uid_or_email, roles):
    sirepo.server.init()

    # POSIT: Uid's are from the base62 charset so an '@' implies an email.
    if '@' in uid_or_email:
        u = sirepo.auth.email.AuthEmailUser.search_by(user_name=uid_or_email)
    else:
        u = sirepo.auth_db.UserRegistration.search_by(uid=uid_or_email)
    assert u, \
        'uid_or_email={} not found'.format(uid_or_email)
    if roles:
        a = sirepo.auth.get_all_roles()
        assert set(roles).issubset(a), \
            'roles={} not a subset valid roles={}'.format(roles, a)
    return u.uid
