# -*- coding: utf-8 -*-
"""auth_db db upgrade

:copyright: Copyright (c) 2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

# uid of user in auth.db in data dir
_UID_WITH_FLASH_ROLE = "pzHuDps6"


def setup_module(module):
    from sirepo import srunit
    import os

    os.environ.update(
        SIREPO_FEATURE_CONFIG_PROPRIETARY_SIM_TYPES="flash",
    )


def test_files():
    """Test file changes for flash db upgrade.

    1. User with flash role has the flash.rpm removed.
    2. User w/o the flash role but has a flash dir is unchanged. This
    is an uncommon case but test whether or not the flash upgrade only
    happens to users with the flash role.

    """
    from pykern import pkio, pkunit
    from pykern.pkunit import pkeq, pkre
    from sirepo import srdb, srunit

    def _check_paths(expect_flash_rpm):
        r = pkio.sorted_glob(srdb.root().join("**", "flash.rpm"))
        l = 1 if expect_flash_rpm else 0
        pkeq(
            l,
            len(r),
            "expect_flash_rpm={}; paths expect={} actual={}",
            expect_flash_rpm,
            l,
            r,
        )
        if expect_flash_rpm:
            pkre(f"user/{_UID_WITH_FLASH_ROLE}", str(r[0]))
        r = pkio.sorted_glob(srdb.root().join("user", "**", "flash"))
        pkeq(2, len(r), "expecting 2 paths found={}", r)

    pkunit.data_dir().join("db").copy(srdb.root())
    _check_paths(True)
    # run db_upgrade
    with srunit.quest_start():
        _check_paths(False)
