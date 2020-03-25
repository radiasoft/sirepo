# -*- coding: utf-8 -*-
u"""test sirepo.pkcli.admin

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest

# NOTE: order of the tests matters, and pytest picks them up in order
# of definition, but we are documenting this with test_1 and test_2 prefixes

def test_1_purge_users_all_premium(fc):
    from pykern.pkunit import pkeq, pkok
    from sirepo import auth_db
    from sirepo import srtime
    from sirepo.pkcli import admin

    d = 1
    res = admin.purge_free_users(days=d, confirm=False)
    pkeq([], res, '{}: no old users so no deletes', res)

    dirs_in_fs = _get_dirs()
    uids_in_db = auth_db.UserRegistration.search_all_for_column('uid')
    pkeq(1, len(dirs_in_fs), '{}: expecting exactly one user dir', dirs_in_fs)
    pkeq(1, len(uids_in_db), '{}: expecting exactly one uid in db', uids_in_db)

    srtime.adjust_time(d + 10)

    res = admin.purge_free_users(days=d, confirm=False)
    pkeq([], res, '{}: all premium users so no deletes', res)
    pkok(dirs_in_fs[0].check(dir=True), '{}: directory not deleted', dirs_in_fs)
    pkeq(
        auth_db.UserRegistration.search_by(uid=uids_in_db[0]).uid,
        uids_in_db[0],
        '{}: expecting uid to still be in db', uids_in_db
    )

def test_2_purge_free_users(fc):
    from pykern import pkunit
    from pykern.pkdebug import pkdp
    from sirepo import srtime
    from sirepo.pkcli import admin
    import sirepo.auth
    import sirepo.auth_db

    u = fc.sr_login_as_guest()
    sirepo.auth_db.UserRole.delete_roles(u, [sirepo.auth.ROLE_PREMIUM])
    pkunit.pkeq(
        2,
        len(sirepo.auth_db.UserRegistration.search_all_for_column('uid')),
    )
    d = 1
    srtime.adjust_time(d + 10)
    v = admin.purge_free_users(days=d, confirm=False)
    pkdp('vvvvvvvv {}', )
    assert 0
    pkunit.pkeq(1, len(v))
    pkunit.pkok(
        u in str(v[0]),
        'expecting uid in path to dir',
    )
    v = admin.purge_free_users(days=d, confirm=True)
    pkunit.pkok(not v[0].check(dir=True), '{}: directory not deleted', v)


def _get_dirs():
    from pykern import pkio
    from sirepo import simulation_db
    g = simulation_db.user_dir_name().join('*')
    return list(pkio.sorted_glob(g))
