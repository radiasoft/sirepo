# -*- coding: utf-8 -*-
u"""test simulation_db operations

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest

def test_last_modified(fc):
    from pykern import pkunit, pkio
    from pykern.pkdebug import pkdp
    import os
    from sirepo import simulation_db, srtime

    def _time(data, data_path, trigger, time):
        data.version = simulation_db._OLDEST_VERSION
        data.models.simulation.pkdel('lastModified')
        simulation_db.write_json(data_path, data)
        trigger.setmtime(time)
        data = fc.sr_sim_data()
        pkunit.pkeq(t * 1000, data.models.simulation.lastModified)
        return data

    d = fc.sr_sim_data()
    w = pkunit.work_dir()
    f = pkio.sorted_glob(w.join('db/user/*/myapp/*/sirepo-data.json'))[0]
    t = srtime.utc_now_as_int() - 123487
    _time(d, f, f, t)
    fc.sr_run_sim(d, 'heightWeightReport')
    _time(
        d,
        f,
        pkio.sorted_glob(f.dirpath().join('*/in.json'))[0],
        t - 10000,
    )


def test_uid():
    _do(
        '/sim-db-file/user/xxx/elegant/RrCoL7rQ/flash_exe-SwBZWpYFR-PqFi81T6rQ8g',
        'yyy',
    )

    _do(
        '/sim-db-file/user/xxx/elegant/RrCoL7rQ/../../../foo',
        'xxx',
    )

    _do(
        '/sim-db-file/user/yyy/invalid/R/flash_exe-SwBZWpYFR-PqFi81T6rQ8g',
        'yyy',
    )

    _do(
        '/sim-db-file/user/yyy/invalid/RrCoL7rQ/flash_exe-SwBZWpYFR-PqFi81T6rQ8g',
        'yyy',
    )

    _do(
        '/sim-db-file/user/HsCFbRrQ/elegant/RrCoL7rQ/{}'.format('x' * 129),
        'HsCFbRrQ',
    )

    _do(
        '/sim-db-file/user/HsCFbRrQ/elegant/RrCoL7rQ/flash_exe-SwBZWpYFR-PqFi81T6rQ8g',
        'HsCFbRrQ',
        expect=False
    )


def _do(path, uid, expect=True):
    from pykern.pkunit import pkeq, pkexcept, pkre
    import sirepo.simulation_db

    if expect:
        with pkexcept(AssertionError):
            sirepo.simulation_db.validate_sim_db_file_path(path, uid)
    else:
        sirepo.simulation_db.validate_sim_db_file_path(path, uid)
