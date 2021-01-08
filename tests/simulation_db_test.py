# -*- coding: utf-8 -*-
u"""test simulation_db operations

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest

def test_uid():
    with pytest.raises(AssertionError):
        _do(
            '/sim-db-file/user/xxx/elegant/RrCoL7rQ/flash_exe-SwBZWpYFR-PqFi81T6rQ8g',
            'yyy',
        )


def test_path_with_dots():
    with pytest.raises(AssertionError):
        _do(
            '/sim-db-file/user/xxx/elegant/RrCoL7rQ/../../../foo',
            'xxx',
        )


def test_sim_id():
    with pytest.raises(AssertionError):
        _do(
            '/sim-db-file/user/yyy/invalid/R/flash_exe-SwBZWpYFR-PqFi81T6rQ8g',
            'yyy',
        )


def test_sim_type():
    with pytest.raises(AssertionError):
        _do(
            '/sim-db-file/user/yyy/invalid/RrCoL7rQ/flash_exe-SwBZWpYFR-PqFi81T6rQ8g',
            'yyy',
        )


def test_long_file():
    with pytest.raises(AssertionError):
        _do(
            '/sim-db-file/user/yyy/invalid/RrCoL7rQ/xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
            'yyy',
        )


def test_validate_sim_db_file_path():
    _do(
        '/sim-db-file/user/HsCFbRrQ/elegant/RrCoL7rQ/flash_exe-SwBZWpYFR-PqFi81T6rQ8g',
        'HsCFbRrQ',
    )


def _do(path, uid):
    from pykern.pkunit import pkeq, pkexcept, pkre
    import sirepo.simulation_db

    sirepo.simulation_db.validate_sim_db_file_path(path, uid)
