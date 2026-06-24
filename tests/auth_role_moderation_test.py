"""test moderated sim types

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern.pkcollections import PKDict

_MODERATED_SIM_TYPE = "myapp"
_NON_MODERATED_SIM_TYPE = "elegant"


def setup_module(module):
    import getpass
    import os

    os.environ.update(
        SIREPO_FEATURE_CONFIG_MODERATED_SIM_TYPES=_MODERATED_SIM_TYPE,
        SIREPO_AUTH_ROLE_MODERATION_MODERATOR_EMAIL=getpass.getuser()
        + "@localhost.localdomain",
    )


def test_moderation(auth_fc):
    from pykern import pkunit
    from sirepo import auth_role, srunit

    a = "applicant@x.x"
    auth_fc.sr_email_login(a, sim_type="srw")
    auth_fc.sr_sim_type_set(_MODERATED_SIM_TYPE)
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
    _save_moderation_reason(
        auth_fc, auth_fc.sr_sim_type, "moderation for moderated sim type"
    )
    _save_moderation_reason(
        auth_fc, _NON_MODERATED_SIM_TYPE, "moderation for sirepo trial access"
    )
    r = auth_fc.sr_post(
        "getModerationRequestRows",
        PKDict(),
        raw_response=True,
    )
    r.assert_http_status(403)
    _approve_all_rows(auth_fc, 2)
    auth_fc.sr_email_login(a, sim_type=_MODERATED_SIM_TYPE)
    r = auth_fc.sr_sim_data()
    pkunit.pkok(r.get("models"), "no models r={}", r)


def test_paid_plan_not_replaced_by_trial_on_approve(auth_fc):
    import datetime
    from pykern import pkunit
    from sirepo import auth_role, srunit

    auth_fc.sr_email_login("paid_user@x.x", sim_type="srw")
    uid = auth_fc.sr_auth_state().uid
    exp = datetime.datetime.now(datetime.UTC).replace(tzinfo=None) + datetime.timedelta(
        days=365
    )
    with srunit.quest_start() as qcall:
        qcall.auth_db.model("UserRole").add_plan(
            auth_role.ROLE_PLAN_BASIC, uid, expiration=exp
        )
    _save_moderation_reason(auth_fc, _NON_MODERATED_SIM_TYPE, "requesting trial access")
    _approve_all_rows(auth_fc, 1)
    with srunit.quest_start() as qcall:
        p = qcall.auth_db.model("UserRole").unchecked_active_plan(uid)
        pkunit.pkeq(auth_role.ROLE_PLAN_BASIC, p.role)
        pkunit.pkok(p.expiration >= exp, "paid plan expiration was truncated")


def test_no_guest(auth_fc):
    auth_fc.sr_login_as_guest(sim_type="srw")
    _save_moderation_reason(
        auth_fc, _MODERATED_SIM_TYPE, "reason for needing moderation"
    ).assert_http_status(403)


def _approve_all_rows(auth_fc, count):
    from pykern import pkunit
    from sirepo import auth_role
    from sirepo.pkcli import roles

    auth_fc.sr_logout()
    auth_fc.sr_email_login("moderator@x.x", sim_type="srw")
    roles.add(auth_fc.sr_auth_state().uid, auth_role.ROLE_ADM)
    r = auth_fc.sr_get("admModerateRedirect")
    r.assert_http_status(200)
    r = auth_fc.sr_post("getModerationRequestRows", PKDict())
    pkunit.pkeq(len(r.rows), count)
    for r in r.rows:
        auth_fc.sr_post(
            "admModerate",
            PKDict(
                uid=r.uid,
                role=r.role,
                status="approve",
            ),
        )
    auth_fc.sr_logout()


def _save_moderation_reason(auth_fc, sim_type, reason):
    return auth_fc.sr_post(
        "saveModerationReason",
        PKDict(simulationType=sim_type, reason=reason),
        raw_response=True,
    )
