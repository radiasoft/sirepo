"""Test getting own and adm jobs.

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

import pytest
import os
from pykern.pkcollections import PKDict
import time


def setup_module(module):
    os.environ.update(
        SIREPO_JOB_DRIVER_LOCAL_SLOTS_PARALLEL="2",
    )


def test_adm_jobs_simple(auth_fc):
    from pykern import pkunit
    from pykern.pkdebug import pkdp

    def _op(fc, sim_type):
        r = fc.sr_post("admJobs", PKDict())
        pkunit.pkeq("srw", r.jobs[0].simulationType)

    _run_sim(auth_fc, _op)


def test_adm_jobs_forbidden(auth_fc):
    from pykern import pkunit
    from pykern.pkdebug import pkdp
    from sirepo import srunit
    import sirepo.auth_role
    import sirepo.pkcli.roles

    def _op(fc, sim_type):
        with srunit.quest_start() as qcall:
            qcall.auth_db.model("UserRole").delete_roles(
                roles=[sirepo.auth_role.ROLE_ADM],
                uid=fc.sr_uid,
            )
        fc.sr_post(
            "admJobs",
            PKDict(simulationType=sim_type),
            raw_response=True,
        ).assert_http_status(403)

    _run_sim(auth_fc, _op)


def test_srw_get_own_jobs(auth_fc):
    from pykern import pkunit
    from pykern.pkdebug import pkdp

    def _op(fc, sim_type):
        r = fc.sr_post("admJobs", PKDict(simulationType=sim_type))
        pkunit.pkeq("srw", r.jobs[0].simulationType)

    _run_sim(auth_fc, _op)


def test_srw_user_see_only_own_jobs(auth_fc):
    from pykern import pkunit
    from pykern.pkdebug import pkdp
    from sirepo import srunit
    from sirepo import auth_role

    def _cancel_job(user, cancel_req):
        _login_as_user(user)
        fc.sr_post("runCancel", cancel_req)

    def _clear_role_db():
        with srunit.quest_start() as qcall:
            qcall.auth_db.model("UserRole").delete_all()

    def _get_jobs(adm, job_count):
        r = fc.sr_post("admJobs" if adm else "ownJobs", PKDict(simulationType=t))
        pkunit.pkeq(
            job_count,
            len(r.jobs),
            "job_count={} len_r={} r={}",
            len(r.jobs),
            job_count,
            r,
        )

    def _get_simulation_running():
        d = auth_fc.sr_sim_data(sim_name=n, sim_type="srw")
        r = fc.sr_post(
            "runSimulation",
            PKDict(
                models=d.models,
                report=m,
                simulationId=d.models.simulation.simulationId,
                simulationType=d.simulationType,
            ),
        )
        try:
            for _ in range(10):
                if r.state == "running":
                    return r.nextRequest
                r = fc.sr_post("runStatus", r.nextRequest)
                time.sleep(1)
            else:
                pkunit.pkfail("Never entered running state")
        except Exception:
            fc.sr_post("runCancel", r.nextRequest)
            raise

    def _login_as_user(user):
        fc.sr_logout()
        fc.sr_email_login(user, sim_type=t)

    def _make_user_adm(uid):
        from sirepo.pkcli import roles
        import sirepo.auth_role

        roles.add(uid, auth_role.ROLE_ADM)
        with srunit.quest_start() as qcall:
            r = qcall.auth_db.model("UserRole").search_all_for_column(
                "uid", role=sirepo.auth_role.ROLE_ADM
            )
        pkunit.pkeq(1, len(r), "One user with role adm r={}", r)
        pkunit.pkeq(r[0], uid, "Expected same uid as user")

    def _register_both_users():
        fc.sr_email_login(adm_user, sim_type=t)
        u = fc.sr_uid
        fc.sr_logout()
        _make_user_adm(u)
        fc.sr_email_login(non_adm_user, sim_type=t)

    fc = auth_fc
    t = "srw"
    n = "Young's Double Slit Experiment"
    m = "multiElectronAnimation"
    adm_user = "diff@b.c"
    non_adm_user = "x@y.z"
    non_adm_job_cancel_req = adm_job_cancel_req = None
    try:
        _clear_role_db()
        _register_both_users()
        non_adm_job_cancel_req = _get_simulation_running()
        _login_as_user(adm_user)
        adm_job_cancel_req = _get_simulation_running()
        _get_jobs(True, 2)
        _login_as_user(non_adm_user)
        _get_jobs(False, 1)
    finally:
        if non_adm_job_cancel_req:
            _cancel_job(non_adm_user, non_adm_job_cancel_req)
        if adm_job_cancel_req:
            _cancel_job(adm_user, adm_job_cancel_req)


def _run_sim(fc, op):
    from pykern import pkunit

    n = "Young's Double Slit Experiment"
    m = "multiElectronAnimation"
    t = "srw"
    c = None

    fc.sr_login_as_guest(sim_type=t)
    d = fc.sr_sim_data(n)
    try:
        r = fc.sr_post(
            "runSimulation",
            PKDict(
                models=d.models,
                report=m,
                simulationId=d.models.simulation.simulationId,
                simulationType=d.simulationType,
            ),
        )
        c = r.nextRequest
        for _ in range(10):
            if r.state == "running":
                op(fc, t)
                return
            r = fc.sr_post("runStatus", r.nextRequest)
            time.sleep(1)
        else:
            pkunit.pkfail("Never entered running state")
    finally:
        fc.sr_post("runCancel", c)
