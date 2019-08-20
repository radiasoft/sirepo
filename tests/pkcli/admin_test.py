# -*- coding: utf-8 -*-
u"""test sirepo.pkcli.admin

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest

pytest.importorskip('srwl_bl')

def test_purge_users(monkeypatch):
    from pykern.pkunit import pkeq, pkok
    from pykern.pkdebug import pkdp
    from pykern import pkio
    from pykern import pkconfig
    from sirepo import srunit
    srunit.init_auth_db(sim_types='myapp')

    from sirepo.pkcli import admin
    from sirepo import simulation_db
    from sirepo import auth_db
    from sirepo import srtime
    import datetime

    days = 1
    adjusted_time = days + 10

    res = admin.purge_guest_users(days=days, confirm=False)
    pkeq([], res, '{}: no old users so empty')

    g = simulation_db.user_dir_name('*')
    dirs = list(pkio.sorted_glob(g))
    pkeq(1, len(dirs), '{}: expecting exactly one user dir', g)

    uid = dirs[0].basename
    srtime.adjust_time(adjusted_time) 

    monkeypatch.setattr(auth_db, 'guest_uids', lambda: [])
    res = admin.purge_guest_users(days=days, confirm=False)
    pkeq([], res, '{}: no guest users so no deletes')

    monkeypatch.setattr(auth_db, 'guest_uids', lambda: [uid])
    res = admin.purge_guest_users(days=days, confirm=False)
    pkeq(dirs, res, '{}: one guest user so one delete', res)

    res = admin.purge_guest_users(days=days, confirm=True)
    pkeq(dirs, res, '{}: one guest user so one delete', res)
    pkok(not dirs[0].check(dir=True), '{}: directory deleted', res)
