# -*- coding: utf-8 -*-
u"""test simulation_db operations

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest

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
        '/sim-db-file/user/yyy/invalid/RrCoL7rQ/xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
        'yyy',
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
