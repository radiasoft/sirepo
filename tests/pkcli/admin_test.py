# -*- coding: utf-8 -*-
u"""test sirepo.pkcli.admin

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest

pytest.importorskip('srwl_bl')

def get_dirs():
    from pykern import pkio
    from sirepo import simulation_db
    g = simulation_db.user_dir_name('*')
    return list(pkio.sorted_glob(g))

def test_purge_users_no_guests(monkeypatch):
    from pykern.pkunit import pkeq, pkok
    from sirepo import srunit
    srunit.init_auth_db(sim_types='myapp')

    from sirepo.pkcli import admin
    from sirepo import auth
    from sirepo import srtime

    days = 1
    adjusted_time = days + 10

    res = admin.purge_guest_users(days=days, confirm=False)
    pkeq([], res, '{}: no old users so empty')

    dirs = get_dirs()
    pkeq(1, len(dirs), '{}: expecting exactly one user dir', dirs)

    srtime.adjust_time(adjusted_time) 

    monkeypatch.setattr(auth, 'guest_uids', lambda: [])
    res = admin.purge_guest_users(days=days, confirm=False)
    pkeq([], res, '{}: no guest users so no deletes')
    pkok(dirs[0].check(dir=True), '{}: directory not deleted', dirs)


def test_purge_users_guests_present():
    from pykern.pkunit import pkeq, pkok
    from sirepo import srunit
    srunit.init_auth_db(sim_types='myapp')

    from sirepo.pkcli import admin
    from sirepo import srtime

    days = 1
    adjusted_time = days + 10

    dirs = get_dirs() 
    srtime.adjust_time(adjusted_time) 

    res = admin.purge_guest_users(days=days, confirm=False)
    pkeq(dirs, res, '{}: one guest user so one delete', res)

    res = admin.purge_guest_users(days=days, confirm=True)
    pkeq(dirs, res, '{}: one guest user so one delete', res)
    pkok(not dirs[0].check(dir=True), '{}: directory deleted', res)
