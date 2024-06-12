"""test moderated sim types

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern.pkcollections import PKDict


def setup_module(module):
    import getpass
    import os

    os.environ.update(
        SIREPO_FEATURE_CONFIG_MODERATED_SIM_TYPES="myapp",
        SIREPO_AUTH_ROLE_MODERATION_MODERATOR_EMAIL=getpass.getuser()
        + "@localhost.localdomain",
    )


def test_moderation(auth_fc):
    from pykern import pkunit
    from sirepo import auth_role, srunit
    from sirepo.pkcli import roles

    auth_fc.sr_email_login("x@x.x", sim_type="srw")
    auth_fc.sr_sim_type_set("myapp")
    with srunit.quest_start() as qcall:
        qcall.auth_db.model("UserRole").delete_all_for_column_by_values(
            "role", [auth_role.for_sim_type(auth_fc.sr_sim_type)]
        )
        qcall.auth_db.model("UserRoleModeration").delete_all_for_column_by_values(
            "role", [auth_role.for_sim_type(auth_fc.sr_sim_type)]
        )
    auth_fc.assert_post_will_redirect(
        "moderation-request",
        "listSimulations",
        PKDict(simulationType=auth_fc.sr_sim_type),
        redirect=False,
    )
    auth_fc.sr_post(
        "saveModerationReason",
        PKDict(
            simulationType=auth_fc.sr_sim_type,
            reason="reason for needing moderation",
        ),
    )
    r = auth_fc.sr_post(
        "getModerationRequestRows",
        PKDict(),
        raw_response=True,
    )
    r.assert_http_status(403)
    roles.add(auth_fc.sr_auth_state().uid, auth_role.ROLE_ADM)
    r = auth_fc.sr_get("admModerateRedirect")
    r.assert_http_status(200)
    r = auth_fc.sr_post("getModerationRequestRows", PKDict())
    pkunit.pkeq(len(r.rows), 1)
    auth_fc.sr_post(
        "admModerate",
        PKDict(
            uid=r.rows[0].uid,
            role=r.rows[0].role,
            status="approve",
        ),
    )
    r = auth_fc.sr_sim_data()
    pkunit.pkok(r.get("models"), "no models r={}", r)


def test_no_guest(auth_fc):
    from pykern import pkunit
    from pykern.pkdebug import pkdp
    from pykern.pkcollections import PKDict

    auth_fc.sr_login_as_guest(sim_type="srw")
    r = auth_fc.sr_post(
        "saveModerationReason",
        PKDict(
            simulationType="myapp",
            reason="reason for needing moderation",
        ),
        raw_response=True,
    )
    r.assert_http_status(403)
