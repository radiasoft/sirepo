"""auth_db db upgrade

:copyright: Copyright (c) 2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from sirepo import srunit
import pytest


def setup_module(module):
    from sirepo import srunit

    srunit.setup_srdb_root()


def test_do_all():
    """See if user gets migrated"""
    from sirepo import srunit, auth_db, db_upgrade
    from pykern import pkunit, pkdebug
    import os

    f = auth_db.db_filename()
    pkunit.data_dir().join(f.basename).copy(f)
    with srunit.quest_start() as qcall:
        # the db_upgrade happens in quest_start, the following tests idempotency
        db_upgrade.do_all(qcall)
    a = f.new(ext="txt")
    os.system(
        "sqlite3 '{}' .dump | perl -p -e '{}' > '{}'".format(
            f,
            r"s/\d{4}-\d\d-\d\d\s+[\d:]+\.\d+//",
            a,
        ),
    )
    pkunit.file_eq(a.basename, actual_path=a)
