"""test Sirepo Trial plan

:copyright: Copyright (c) 2025 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

_EXPIRATION_DAYS = 2


def test_expired_trial_no_run_sim(auth_fc):
    from pykern.pkcollections import PKDict
    from sirepo.pkcli import roles
    from pykern import pkunit
    import datetime

    u = auth_fc.sr_email_login("e@e.e")
    roles.delete(u, "premium")
    l = roles.list_with_expiration(u)
    pkunit.pkok(
        not any(filter(lambda x: x.role == "trial", l)),
        "unexpected trial in roles={}",
        l,
    )
    roles.add(u, "trial", expiration=_EXPIRATION_DAYS)
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
