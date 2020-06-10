# -*- coding: utf-8 -*-
u"""Test role management operations

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest

def test_flash_change_role_change_lib_files(auth_fc):
    from pykern import pkio
    from pykern import pkunit
    import sirepo.auth
    import sirepo.auth_db
    import sirepo.pkcli.roles
    import sirepo.srdb

    def _change_role(add=True):
        f = getattr(sirepo.pkcli.roles, 'add_roles')
        if not add:
            f = getattr(sirepo.pkcli.roles, 'delete_roles')
        f(
            fc.sr_auth_state().uid,
            sirepo.auth.role_for_sim_type(fc.sr_sim_type),
        )

    def _check_file(exists=True):
        pkunit.pkeq(
            [_proprietary_file] if exists else [],
            [x.basename for x in pkio.walk_tree(fc.sr_user_dir(), _proprietary_file)],
        )

    pkunit.data_dir().join('db').copy(sirepo.srdb.root())
    _proprietary_file = 'flash.rpm'
    fc = auth_fc
    fc.sr_email_register('a@b.c', sim_type='flash')

    r = fc.sr_post('listSimulations', {'simulationType': fc.sr_sim_type}, raw_response=True)
    pkunit.pkeq(403, r.status_code)

    _check_file(exists=False)
    _change_role(add=True)
    _check_file(exists=True)
    _change_role(add=False)
    _check_file(exists=False)


def test_flash_list_role_by_email(auth_fc):
    from pykern import pkunit
    import sirepo.pkcli.roles

    e = 'a@b.c'
    r = ['premium']
    auth_fc.sr_email_register(e, sim_type='flash')
    sirepo.pkcli.roles.add_roles(e, *r)
    pkunit.pkeq(r, sirepo.pkcli.roles.list_roles(e))
    pkunit.pkeq(r, sirepo.pkcli.roles.list_roles(auth_fc.sr_auth_state().uid))
