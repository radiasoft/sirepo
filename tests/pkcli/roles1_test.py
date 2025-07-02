"""Test role management operations

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

import os
import pytest


def setup_module(module):
    os.environ.update(
        SIREPO_FEATURE_CONFIG_PROPRIETARY_SIM_TYPES="flash",
    )


def test_flash_change_role_change_lib_files(auth_fc):
    from pykern import pkio
    from pykern import pkunit
    from sirepo import auth_role, srdb
    from sirepo.pkcli import roles

    def _change_role(add=True):
        f = getattr(roles, "add" if add else "delete")
        f(fc.sr_uid, auth_role.for_sim_type(fc.sr_sim_type))

    def _check_file(exists=True):
        pkunit.pkeq(
            [_proprietary_file] if exists else [],
            [x.basename for x in pkio.walk_tree(fc.sr_user_dir(), _proprietary_file)],
        )

    pkunit.data_dir().join("db").copy(srdb.root())
    _proprietary_file = "flash.tar.gz"
    fc = auth_fc

    fc.sr_email_login("a@b.c", sim_type="flash")
    r = fc.sr_post(
        "listSimulations", {"simulationType": fc.sr_sim_type}, raw_response=True
    )
    r.assert_http_status(403)
    _check_file(exists=False)
    _change_role(add=True)
    _check_file(exists=True)
    _change_role(add=False)
    _check_file(exists=False)


def test_flash_list_role_by_email(auth_fc):
    from pykern import pkunit
    from sirepo import srdb
    from sirepo.pkcli import roles

    e = "a@b.c"
    r = "premium"
    pkunit.data_dir().join("db").copy(srdb.root())
    auth_fc.sr_email_login(e, sim_type="flash")
    roles.add(e, r)
    pkunit.pkok(r in roles.list(e), "expected user {} to have role {}", e, r)
    pkunit.pkok(
        r in roles.list(auth_fc.sr_uid),
        "expected user {} to have role {}",
        auth_fc.sr_uid,
        r,
    )
