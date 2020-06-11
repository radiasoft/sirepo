# -*- coding: utf-8 -*-
u"""CRUD operations for user roles

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp
from sirepo.pkcli import admin
import pykern.pkcli
import sirepo.auth
import sirepo.auth.email
import sirepo.auth_db
import sirepo.server


def add_roles(uid_or_email, *roles):
    """Assign roles to a user
    Args:
        uid_or_email (str): Uid or email of the user
        *args: The roles to assign to the user
    """
    sirepo.auth_db.UserRole.add_roles(
        _args(uid_or_email, roles),
        roles,
    )



def delete_roles(uid_or_email, *roles):
    """Remove roles assigned to user
    Args:
        uid_or_email (str): Uid or email of the user
        *args: The roles to delete
    """
    sirepo.auth_db.UserRole.delete_roles(
        _args(uid_or_email, roles),
        roles,
    )


def list_roles(uid_or_email):
    """List all roles assigned to a user
    Args:
        uid_or_email (str): Uid or email of the user
    """
    return sirepo.auth_db.UserRole.search_all_for_column(
        'role',
        uid=_args(uid_or_email, []),
    )


# TODO(e-carlin): This only works for email auth or using a uid
# doesn't work for other auth methods (ex GitHub)
def _args(uid_or_email, roles):
    sirepo.server.init()

    # POSIT: Uid's are from the base62 charset so an '@' implies an email.
    if '@' in uid_or_email:
        u = sirepo.auth.email.AuthEmailUser.search_by(user_name=uid_or_email)
    else:
        u = sirepo.auth_db.UserRegistration.search_by(uid=uid_or_email)
    if not u:
        pykern.pkcli.command_error('uid_or_email={} not found', uid_or_email)
    if roles:
        a = sirepo.auth.get_all_roles()
        assert set(roles).issubset(a), \
            'roles={} not a subset valid all_roles={}'.format(roles, a)
    return u.uid
