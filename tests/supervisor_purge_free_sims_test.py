"""Test purging of free users "old" simulations.

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

_CACHE_AND_SIM_PURGE_PERIOD = 3
_PURGE_FREE_AFTER_DAYS = 1


def setup_module(module):
    import os

    os.environ.update(
        SIREPO_JOB_SUPERVISOR_JOB_CACHE_SECS=str(_CACHE_AND_SIM_PURGE_PERIOD),
        SIREPO_JOB_SUPERVISOR_RUN_DIR_LIFETIME=str(_PURGE_FREE_AFTER_DAYS) + "d",
        SIREPO_JOB_SUPERVISOR_PURGE_CHECK_INTERVAL="00:00:0{}".format(
            _CACHE_AND_SIM_PURGE_PERIOD
        ),
    )


def test_myapp_free_user_sim_purged(auth_fc):
    from pykern import pkunit, pkcollections, pkio, pkunit
    from pykern.pkdebug import pkdp
    from sirepo import auth_role, const, srdb
    import time

    model = "heightWeightReport"

    def _check_run_dir(should_exist=0):
        f = pkio.walk_tree(fc.sr_user_dir(), file_re=model)
        pkunit.pkeq(
            should_exist,
            len(f),
            "incorrect file count user_dir={} file_re={model}",
            fc.sr_user_dir(),
            model,
        )

    def _make_invalid_job():
        d = srdb.supervisor_dir()
        d.ensure(dir=True)
        # This will be the first file found and cause purge_non_premium to raise
        pkunit.data_dir().join("00000001-JzccRZNg-heightWeightReport.json").copy(d)

    def _make_user_premium(uid):
        from sirepo import srunit
        from sirepo.pkcli import roles

        roles.add(
            uid,
            auth_role.ROLE_PAYMENT_PLAN_PREMIUM,
        )
        with srunit.quest_start() as qcall:
            r = qcall.auth_db.model("UserRole").search_all_for_column(
                "uid", role=auth_role.ROLE_PAYMENT_PLAN_PREMIUM
            )
        pkunit.pkeq([uid], r, "expecting one premium user with same id")

    def _run_sim(data):
        r = fc.sr_run_sim(data, model)
        r.simulationType = fc.sr_sim_type
        r.report = model
        r.update(data)
        return r

    def _status_eq(next_req, status):
        pkunit.pkeq(status, fc.sr_post("runStatus", next_req).state)

    fc = auth_fc
    user_free = "free@b.c"
    user_premium = "premium@x.y"
    fc.sr_email_login(user_free)
    fc.sr_email_login(user_premium)
    _make_user_premium(fc.sr_uid)
    _make_invalid_job()
    next_req_premium = _run_sim(fc.sr_sim_data())
    fc.sr_email_login(user_free)
    next_req_free = _run_sim(fc.sr_sim_data())
    with fc.sr_adjust_time(_PURGE_FREE_AFTER_DAYS + 1):
        time.sleep(_CACHE_AND_SIM_PURGE_PERIOD + 1)
        _status_eq(next_req_free, "job_run_purged")
        _check_run_dir(should_exist=0)
        fc.sr_email_login(user_premium)
        _status_eq(next_req_premium, "completed")
        _check_run_dir(should_exist=6)


def test_elegant_no_frame_after_purge(auth_fc):
    """This test fails if test_myapp_free_user_sim_purged fails"""
    from pykern import pkunit
    from pykern.pkcollections import PKDict
    from pykern.pkdebug import pkdp
    import time

    fc = auth_fc
    user_free = "free@b.c"
    fc.sr_email_login(user_free)
    d = fc.sr_sim_data(sim_name="Compact Storage Ring", sim_type="elegant")
    r = fc.sr_run_sim(d, "animation")
    with fc.sr_adjust_time(_PURGE_FREE_AFTER_DAYS + 1):
        time.sleep(_CACHE_AND_SIM_PURGE_PERIOD + 1)
        s = fc.sr_post(
            "runStatus",
            PKDict(
                computeJobHash=r.computeJobHash,
                models=d.models,
                report="animation",
                simulationId=d.models.simulation.simulationId,
                simulationType=d.simulationType,
            ),
        )
        pkunit.pkeq("job_run_purged", s.state)
        pkunit.pkeq(
            0,
            s.frameCount,
        )
