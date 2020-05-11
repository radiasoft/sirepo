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
        SIREPO_JOB_SUPERVISOR_PURGE_NON_PREMIUM_AFTER_DAYS=str(_PURGE_FREE_AFTER_DAYS),
        SIREPO_JOB_SUPERVISOR_PURGE_NON_PREMIUM_TASK_SECS='00:00:0{}'.format(_CACHE_AND_SIM_PURGE_PERIOD),
    )


def test_myapp_free_user_sim_purged(auth_fc):
    from pykern import pkio
    from pykern import pkunit
    from pykern.pkdebug import pkdp
    import sirepo.auth

    def _check_run_dir(should_exist=0):
        f = pkio.walk_tree(fc.sr_user_dir(), file_re=m)
        pkunit.pkeq(should_exist, len(f))

    def _make_user_premium(uid):
        sirepo.auth_db.UserRole.add_roles(uid, [sirepo.auth.ROLE_PREMIUM])
        r = sirepo.auth_db.UserRole.search_all_for_column('uid')
        pkunit.pkeq(r, [uid], 'expecting one premium user with same id')

    def sr_run_sim_on_state_do_op(sim_data, compute_model, state, op):
        c = None
        try:
            r = fc.sr_post(
                'runSimulation',
                PKDict(
                    models=sim_data.models,
                    report=compute_model,
                    simulationId=sim_data.models.simulation.simulationId,
                    simulationType=sim_data.simulationType,
                )
            )
            c = r.nextRequest
            for _ in range(10):
                if r.state == state:
                    return op(c)
                r = fc.sr_post('runStatus', r.nextRequest)
                time.sleep(1)
            else:
                pkunit.pkfail('Never entered state {}', state)
        except Exception:
            if c:
                fc.sr_post('runCancel', c)
            raise

    def _run_sim(data):
        r = fc.sr_run_sim(data, m)
        r.simulationType = fc.sr_sim_type
        r.report = m
        r.update(data)
        return r

    def _status_eq(next_req, status):
        pkunit.pkeq(
            status,
            fc.sr_post('runStatus', next_req).state
        )

    fc = auth_fc
    m = 'heightWeightReport'
    user_free = 'free@b.c'
    user_premium = 'premium@x.y'
    fc.sr_email_register(user_free)
    fc.sr_email_register(user_premium)
    _make_user_premium(fc.sr_auth_state().uid)
    next_req_premium = _run_sim(fc.sr_sim_data())
    fc.sr_email_login(user_free)
    next_req_free = _run_sim(fc.sr_sim_data())
    fc.sr_get_json(
        'adjustTime',
        params=PKDict(days=_PURGE_FREE_AFTER_DAYS + 1),
    )
    time.sleep(_CACHE_AND_SIM_PURGE_PERIOD + 1)
    _status_eq(next_req_free, 'job_run_purged')
    _check_run_dir(should_exist=0)
    fc.sr_email_login(user_premium)
    _status_eq(next_req_premium, 'completed')
    _check_run_dir(should_exist=6)
