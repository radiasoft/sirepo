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
    from sirepo import sr_unit

    # Need to initialize first
    sr_unit.init_user_db()

    from sirepo.pkcli import admin
    from sirepo import simulation_db
    from sirepo import server
    import datetime

    res = admin.purge_users(days=1, confirm=False)
    pkeq([], res, '{}: no old users so empty')
    pkdp(simulation_db.user_dir_name('*'))
    g = simulation_db.user_dir_name('*')
    dirs = list(pkio.sorted_glob(g))
    pkeq(1, len(dirs), '{}: expecting exactly one user dir', g)
    uid = dirs[0].basename
    #TODO(robnagler) really want the db to be created, but need
    #  a test oauth class.
    monkeypatch.setattr(server, 'all_uids', lambda: [uid])
    for f in pkio.walk_tree(dirs[0]):
        f.setmtime(f.mtime() - 86400 * 2)
    res = admin.purge_users(days=1, confirm=False)
    pkeq([], res, '{}: all users registered so no deletes')
    monkeypatch.setattr(server, 'all_uids', lambda: [])
    res = admin.purge_users(days=1, confirm=False)
    pkeq(dirs, res, '{}: no users registered so one delete', res)
    pkok(dirs[0].check(dir=True), '{}: nothing deleted', res)
    res = admin.purge_users(days=1, confirm=True)
    pkeq(dirs, res, '{}: no users registered so one delete', res)
    pkok(not dirs[0].check(dir=True), '{}: directory deleted', res)
