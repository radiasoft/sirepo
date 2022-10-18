# -*- coding: utf-8 -*-
"""Test purging of free users "old" simulations.

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest
from pykern.pkcollections import PKDict
import os
import time

_CACHE_AND_SIM_PURGE_PERIOD = 3
_PURGE_FREE_AFTER_DAYS = 1


def setup_module(module):
    os.environ.update(
        SIREPO_JOB_SUPERVISOR_JOB_CACHE_SECS=str(_CACHE_AND_SIM_PURGE_PERIOD),
        SIREPO_JOB_SUPERVISOR_PURGE_NON_PREMIUM_AFTER_SECS=str(_PURGE_FREE_AFTER_DAYS)
        + "d",
        SIREPO_JOB_SUPERVISOR_PURGE_NON_PREMIUM_TASK_SECS="00:00:0{}".format(
            _CACHE_AND_SIM_PURGE_PERIOD
        ),
    )


def test_myapp_free_user_sim_purged(auth_fc):
    from pykern import pkio
    from pykern import pkunit
    from pykern.pkdebug import pkdp
    import sirepo.auth_role

    def _check_run_dir(should_exist=0):
        f = pkio.walk_tree(fc.sr_user_dir(), file_re=m)
        pkunit.pkeq(should_exist, len(f), "incorrect file count")

    def _make_user_premium(uid):
        from sirepo import srunit
        import sirepo.pkcli.roles

        sirepo.pkcli.roles.add_roles(
            uid,
            sirepo.auth_role.ROLE_PAYMENT_PLAN_PREMIUM,
        )
        with srunit.auth_db_session():
            r = sirepo.auth_db.UserRole.search_all_for_column("uid")
        pkunit.pkeq(r, [uid], "expecting one premium user with same id")

    def _run_sim(data):
        r = fc.sr_run_sim(data, m)
        r.simulationType = fc.sr_sim_type
        r.report = m
        r.update(data)
        return r

    def _status_eq(next_req, status):
        pkunit.pkeq(status, fc.sr_post("runStatus", next_req).state)

    fc = auth_fc
    m = "heightWeightReport"
    user_free = "free@b.c"
    user_premium = "premium@x.y"
    fc.sr_email_register(user_free)
    fc.sr_email_register(user_premium)
    _make_user_premium(fc.sr_auth_state().uid)
    next_req_premium = _run_sim(fc.sr_sim_data())
    fc.sr_email_login(user_free)
    next_req_free = _run_sim(fc.sr_sim_data())
    _adjust_time(fc)
    time.sleep(_CACHE_AND_SIM_PURGE_PERIOD + 1)
    _status_eq(next_req_free, "job_run_purged")
    _check_run_dir(should_exist=0)
    fc.sr_email_login(user_premium)
    _status_eq(next_req_premium, "completed")
    _check_run_dir(should_exist=7)
    _adjust_time(fc, restore=True)


def test_elegant_no_frame_after_purge(auth_fc):
    from pykern import pkunit
    from pykern.pkcollections import PKDict
    from pykern.pkdebug import pkdp

    fc = auth_fc
    user_free = "free@b.c"
    fc.sr_email_register(user_free)
    d = fc.sr_sim_data(sim_name="Compact Storage Ring", sim_type="elegant")
    r = fc.sr_run_sim(d, "animation")
    _adjust_time(fc)
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
    _adjust_time(fc, restore=True)


def _adjust_time(fc, restore=False):
    fc.sr_get_json(
        "adjustTime",
        params=PKDict(
            days=(-1 if restore else 1) * (_PURGE_FREE_AFTER_DAYS + 1),
        ),
    )
