"""test Sirepo Trial plan

:copyright: Copyright (c) 2025 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

_EXPIRATION_DAYS = 2


def test_guest_trial_no_expiration(auth_fc):
    from pykern import pkunit
    from sirepo.pkcli import roles

    u = auth_fc.sr_login_as_guest()
    l = roles.list_with_expiration(u)
    for r in l:
        if r.role == "trial" and r.expiration is None:
            return
    pkunit.pkfail(f"no trial with no expiration in roles={l}")


def test_expired_trial_no_run_sim(auth_fc):
    from pykern.pkcollections import PKDict
    from sirepo.pkcli import roles
    import datetime

    u = auth_fc.sr_email_login("e@e.e")
    roles.add_or_update(u, "trial", expiration=_EXPIRATION_DAYS)
    d = auth_fc.sr_sim_data()
    auth_fc.sr_run_sim(d, "heightWeightReport")
    with auth_fc.sr_adjust_time(_EXPIRATION_DAYS + 1):
        auth_fc.sr_post(
            "runSimulation",
            PKDict(
                models=d.models,
                report="heightWeightReport",
                simulationId=d.models.simulation.simulationId,
                simulationType=d.simulationType,
            ),
            raw_response=True,
        ).assert_http_status(402)
