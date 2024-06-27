"""Test pkcli.admin.disable_user

:copyright: Copyright (c) 2024 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

import pytest


def test_disable_user(fc):
    from pykern.pkcollections import PKDict
    from pykern.pkunit import pkeq, pkok
    import sirepo.auth_role
    import sirepo.pkcli.roles
    import sirepo.srunit

    pkok(
        sirepo.auth_role.ROLE_USER in fc.sr_auth_state().roles,
        "{} not found in roles",
        sirepo.auth_role.ROLE_USER,
    )
    fc.sr_post(
        "listSimulations", {"simulationType": fc.sr_sim_type}, raw_response=True
    ).assert_success()
    sirepo.pkcli.roles.disable_user(fc.sr_uid, fc.sr_uid)
    pkok(
        sirepo.auth_role.ROLE_USER not in fc.sr_auth_state().roles,
        "{} found in roles",
        sirepo.auth_role.ROLE_USER,
    )
    with sirepo.srunit.quest_start() as qcall:
        pkeq(
            sirepo.auth_role.ModerationStatus.DENY,
            qcall.auth_db.model("UserRoleModeration").get_status(
                sirepo.auth_role.ROLE_USER, uid=fc.sr_uid
            ),
        )
    fc.sr_post(
        "listSimulations", {"simulationType": fc.sr_sim_type}, raw_response=True
    ).assert_http_status(403)
