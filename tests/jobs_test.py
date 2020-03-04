# -*- coding: utf-8 -*-
u"""Test getting own and adm jobs.

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest
import os
from pykern.pkcollections import PKDict
import time

pytestmark = pytest.mark.skipif(
    os.environ.get('SIREPO_FEATURE_CONFIG_JOB') != '1',
    reason='SIREPO_FEATURE_CONFIG_JOB != 1'
)


def xtest_srw_adm_jobs(fc):
    from pykern import pkunit
    from pykern.pkdebug import pkdp
    n = "Young's Double Slit Experiment"
    m = 'multiElectronAnimation'
    d = fc.sr_sim_data(n)
    l = 8
    cancel = None
    try:
        r = fc.sr_post(
            'runSimulation',
            PKDict(
                models=d.models,
                report=m,
                simulationId=d.models.simulation.simulationId,
                simulationType=d.simulationType,
            )
        )
        cancel = r.nextRequest
        for _ in range(10):
            if r.state == 'running':
                r = fc.sr_post(
                    'admJobs',
                    PKDict(simulationType=d.simulationType)
                )
                pkunit.pkeq(8, len(r.header))
                pkunit.pkeq(8, len(r.rows[0]))
                pkunit.pkeq('srw', r.rows[0][0])
                return
            r = fc.sr_post('runStatus', r.nextRequest)
            time.sleep(1)
        else:
            pkunit.pkfail('Never entered running state')
    finally:
        fc.sr_post('runCancel', cancel)


def xtest_srw_adm_jobs_forbidden(fc):
    from pykern import pkunit
    from pykern.pkdebug import pkdp

    n = "Young's Double Slit Experiment"
    m = 'multiElectronAnimation'
    d = fc.sr_sim_data(n)
    cancel = None
    try:
        r = fc.sr_post(
            'runSimulation',
            PKDict(
                models=d.models,
                report=m,
                simulationId=d.models.simulation.simulationId,
                simulationType=d.simulationType,
            )
        )
        cancel = r.nextRequest
        for _ in range(10):
            if r.state == 'running':
                import sirepo.auth_db
                sirepo.auth_db.UserRole.delete_all_for_column_by_values('uid', [fc.sr_auth_state().uid, ])
                r = fc.sr_post(
                    'admJobs',
                    PKDict(simulationType=d.simulationType),
                    raw_response=True,
                )
                pkunit.pkeq(403, r.status_code)
                return
            r = fc.sr_post('runStatus', r.nextRequest)
            time.sleep(1)
        else:
            pkunit.pkfail('Never entered running state')
    finally:
        fc.sr_post('runCancel', cancel)


def xtest_srw_get_own_jobs(fc):
    from pykern import pkunit
    from pykern.pkdebug import pkdp
    n = "Young's Double Slit Experiment"
    m = 'multiElectronAnimation'
    d = fc.sr_sim_data(n)
    l = 6
    cancel = None
    try:
        r = fc.sr_post(
            'runSimulation',
            PKDict(
                models=d.models,
                report=m,
                simulationId=d.models.simulation.simulationId,
                simulationType=d.simulationType,
            )
        )
        cancel = r.nextRequest
        for _ in range(10):
            if r.state == 'running':
                r = fc.sr_post(
                    'admJobs',
                    PKDict(simulationType=d.simulationType)
                )
                pkunit.pkeq(8, len(r.header))
                pkunit.pkeq(8, len(r.rows[0]))
                pkunit.pkeq('srw', r.rows[0][0])
                return
            r = fc.sr_post('runStatus', r.nextRequest)
            time.sleep(1)
        else:
            pkunit.pkfail('Never entered running state')
    finally:
        fc.sr_post('runCancel', cancel)


def test_srw_user_see_only_own_jobs(auth_fc):
    from pykern import pkunit
    from pykern.pkdebug import pkdp
    import sirepo.auth_db
    import sirepo.auth

    n = "Young's Double Slit Experiment"
    m = 'multiElectronAnimation'
    d = auth_fc.sr_sim_data(n)

    def _login_as_user(user):
        fc.sr_post('authEmailLogin', {'email': user, 'simulationType': fc.sr_sim_type})

    def _get_simulation_running():
        fc.sr_post('authEmailLogin', {'email': user_b, 'simulationType': fc.sr_sim_type})
        r = fc.sr_post(
            'runSimulation',
            PKDict(
                models=d.models,
                report=m,
                simulationId=d.models.simulation.simulationId,
                simulationType=d.simulationType,
            )
        )
        for _ in range(10):
            if r.state == 'running':
                return
            r = fc.sr_post('runStatus', r.nextRequest)
            time.sleep(1)
        else:
            pkunit.pkfail('Never entered running state')

    def _register_both_users():
        r = fc.sr_post('authEmailLogin', {'email': user_a, 'simulationType': fc.sr_sim_type})
        fc.sr_email_confirm(fc, r)
        fc.sr_post('authCompleteRegistration', {'displayName': 'abc', 'simulationType': fc.sr_sim_type,},)
        fc.sr_get('authLogout', {'simulation_type': fc.sr_sim_type})
        uid = fc.sr_auth_state().uid
        r = fc.sr_post('authEmailLogin', {'email': user_b, 'simulationType': fc.sr_sim_type})
        fc.sr_email_confirm(fc, r, 'xyz')
        sirepo.auth_db.UserRole.add_roles(uid, [sirepo.auth.ROLE_ADM])
        r = sirepo.auth_db.UserRole.search_all_for_column('uid')
        pkunit.pkeq(1, len(r))
        pkunit.pkeq(r[0], uid)
    # t = 'srw'
    # n = "Young's Double Slit Experiment"
    # m = 'multiElectronAnimation'
    # d = fc.sr_sim_data(n)
    fc = auth_fc

    user_a = 'diff@b.c'
    user_b = 'x@y.z'

    _register_both_users()
    # _login_as_user(user)
    _get_simulation_running()
