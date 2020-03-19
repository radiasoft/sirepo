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

SECS = 3
DAYS = 1


def setup_module(module):
    os.environ.update(
        SIREPO_JOB_SUPERVISOR_JOB_CACHE_SECS=str(SECS),
        SIREPO_JOB_SUPERVISOR_TEST_PURGE_FREQUENCY_SECS=str(SECS),
        SIREPO_JOB_SUPERVISOR_PURGE_FREE_AFTER_DAYS=str(DAYS),
    )


def test_myapp_free_user_sim_purged(auth_fc):
    from pykern import pkio
    from pykern import pkunit
    from pykern.pkdebug import pkdp
    import sirepo.auth

    def _check_run_dir(should_exist=False):
        def _filter(elem):
            return 'heightWeightReport' in str(elem)

        f = pkio.sorted_glob(pkunit.work_dir().join(
            'db',
            'user',
            fc.sr_auth_state().uid,
            'myapp',
            '*',
            '*',
            ),
        )
        f = filter(_filter, f)
        if should_exist:
            pkunit.pkeq(1, len(f))
            return
        pkunit.pkeq(0, len(f))

    def _login_as_user(user):
        fc.sr_logout()
        r = fc.sr_post(
            'authEmailLogin',
            PKDict(email=user, simulationType=fc.sr_sim_type),
        )
        fc.sr_email_confirm(fc, r)

    def _make_user_premium(uid):
        sirepo.auth_db.UserRole.add_roles(uid, [sirepo.auth.ROLE_PREMIUM])
        r = sirepo.auth_db.UserRole.search_all_for_column('uid')
        pkunit.pkeq(1, len(r), 'One user with role premium r={}', r)
        pkunit.pkeq(r[0], uid, 'Expected same uid as user')

    def _run_sim(data):
        from pykern import pkunit
        c = None
        try:
            r = fc.sr_post(
                'runSimulation',
                PKDict(
                    models=data.models,
                    report=m,
                    simulationId=data.models.simulation.simulationId,
                    simulationType=data.simulationType,
                )
            )
            c = r.nextRequest
            for _ in range(10):
                if r.state == 'completed':
                    return c
                r = fc.sr_post('runStatus', r.nextRequest)
                time.sleep(1)
            else:
                pkunit.pkfail('Never entered running state')
        except Exception:
            if c:
                fc.sr_post('runCancel', c)
            raise

    def _register_both_users():
        def _register(email):
            r = fc.sr_post(
                'authEmailLogin',
                PKDict(email=email, simulationType=fc.sr_sim_type),
            )
            fc.sr_email_confirm(fc, r)
            fc.sr_post(
                'authCompleteRegistration',
                PKDict(displayName=email, simulationType=fc.sr_sim_type),
            )
        _register(user_free)
        _register(user_premium)
        _make_user_premium(fc.sr_auth_state().uid)

    def _status_eq(next_req, status):
        pkunit.pkeq(
            status,
            fc.sr_post('runStatus', next_req).state
        )

    fc = auth_fc
    m = 'heightWeightReport'
    user_free = 'free@b.c'
    user_premium = 'premium@x.y'
    _register_both_users()
    next_req_premium = _run_sim(fc.sr_sim_data())
    _login_as_user(user_free)
    next_req_free = _run_sim(fc.sr_sim_data())
    fc.sr_get_json(
        'adjustTime',
        params=PKDict(days=DAYS + 1),
    )
    time.sleep(SECS + 1)
    _status_eq(next_req_free, 'free_user_purged')
    _check_run_dir(should_exist=False)
    _login_as_user(user_premium)
    _status_eq(next_req_premium, 'completed')
    _check_run_dir(should_exist=True)
