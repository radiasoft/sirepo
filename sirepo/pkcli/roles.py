# -*- coding: utf-8 -*-
u"""CRUD operations for user roles

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp
from sirepo.pkcli import admin
import sirepo.auth
import sirepo.auth_db
import sirepo.server


def add_roles(uid, *args):  # TODO(e-carlin): roles arg
    """Assign roles to a user
    Args:
        uid (str): Uid of the user
        *args: The roles to assign to the user
    """
    _check_uid_and_roles(uid, args)
    sirepo.auth_db.UserRole.add_roles(uid, args)
    admin.audit_protected_lib_files(uid)



def delete_roles(uid, *args):
    """Remove roles assigned to user
    Args:
        uid (str): Uid of the user
        *args: The roles to delete
    """
    _check_uid_and_roles(uid, args)
    sirepo.auth_db.UserRole.delete_roles(uid, args)
    admin.audit_protected_lib_files(uid)


def list_roles(uid):
    """List all roles assigned to a user
    Args:
        uid (str): Uid of the user
    """
    _check_uid_and_roles(uid, [])
    return sirepo.auth_db.UserRole.search_all_for_column('role', uid=uid)


def _check_uid_and_roles(uid, roles):
    sirepo.server.init()
    assert sirepo.auth_db.UserRegistration.search_by(uid=uid), \
        'uid {} not found'.format(uid)
    if roles:
        a = sirepo.auth.get_all_roles()
        assert set(roles).issubset(a), \
            'roles={} not a subset valid roles={}'.format(roles, a)
