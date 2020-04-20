# -*- coding: utf-8 -*-
u"""test sirepo.pkcli.admin

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest

# NOTE: order of the tests matters, and pytest picks them up in order
# of definition, but we are documenting this with test_1 and test_2 prefixes

def test_1_purge_users_no_guests(monkeypatch, auth_fc):
    from sirepo import auth_db
    from pykern.pkunit import pkeq, pkok
    from sirepo import srunit
    from sirepo.pkcli import admin
    from sirepo import auth
    from sirepo import srtime

    if not auth_fc.sr_uid:
        auth_fc.sr_login_as_guest()
    days = 1
    adjusted_time = days + 10

    res = admin.purge_guest_users(days=days, confirm=False)
    pkeq({}, res, '{}: no old users so no deletes', res)

    dirs_in_fs = _get_dirs()
    uids_in_db = auth_db.UserRegistration.search_all_for_column('uid')
    pkeq(1, len(dirs_in_fs), '{}: expecting exactly one user dir', dirs_in_fs)
    pkeq(1, len(uids_in_db), '{}: expecting exactly one uid in db', uids_in_db)

    srtime.adjust_time(adjusted_time)

    monkeypatch.setattr(auth, 'guest_uids', lambda: [])
    res = admin.purge_guest_users(days=days, confirm=False)
    pkeq({}, res, '{}: no guest users so no deletes', res)
    pkok(dirs_in_fs[0].check(dir=True), '{}: directory not deleted', dirs_in_fs)
    pkeq(
        auth_db.UserRegistration.search_by(uid=uids_in_db[0]).uid,
        uids_in_db[0],
        '{}: expecting uid to still be in db', uids_in_db
    )

def test_2_purge_users_guests_present(auth_fc):
    from sirepo import auth_db
    from pykern.pkunit import pkeq, pkok
    from sirepo import srunit
    from sirepo.pkcli import admin
    from sirepo import srtime

    if not auth_fc.sr_uid:
        auth_fc.sr_login_as_guest()
    days = 1
    adjusted_time = days + 10
    dirs_in_fs = _get_dirs()
    uids_in_db = auth_db.UserRegistration.search_all_for_column('uid')
    dirs_and_uids = {dirs_in_fs[0]: uids_in_db[0]}
    srtime.adjust_time(adjusted_time)

    res = admin.purge_guest_users(days=days, confirm=False)
    pkeq(dirs_and_uids, res, '{}: one guest user so one dir and uid to delete', res)

    res = admin.purge_guest_users(days=days, confirm=True)
    pkeq(dirs_and_uids, res, '{}: one guest user so one dir and uid to delete', res)
    pkok(
        not list(res.keys())[0].check(dir=True),
        '{}: directory deleted',
        res,
    )
    pkeq(
        auth_db.UserRegistration.search_by(uid=list(res.values())[0]),
        None,
        '{}: expecting uid to deleted from db', res
    )

def _get_dirs():
    from pykern import pkio
    from sirepo import simulation_db
    g = simulation_db.user_dir_name().join('*')
    return list(pkio.sorted_glob(g))
