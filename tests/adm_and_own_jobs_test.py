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


def setup_module(module):
    os.environ.update(
        SIREPO_JOB_DRIVER_LOCAL_SLOTS_PARALLEL='2',
    )


def test_adm_jobs(auth_fc):
    from pykern import pkunit
    from pykern.pkdebug import pkdp

    def _op(fc, sim_type):
        r = fc.sr_post(
            'admJobs',
            PKDict(simulationType=sim_type)
        )
        pkunit.pkeq(len(r.rows[0]), len(r.header))
        pkunit.pkeq('srw', r.rows[0][0])

    _run_sim(auth_fc, _op)


def test_adm_jobs_forbidden(auth_fc):
    from pykern import pkunit
    from pykern.pkdebug import pkdp

    def _op(fc, sim_type):
        import sirepo.auth_db
        sirepo.auth_db.UserRole.delete_all_for_column_by_values('uid', [fc.sr_auth_state().uid, ])
        r = fc.sr_post(
            'admJobs',
            PKDict(simulationType=sim_type),
            raw_response=True,
        )
        pkunit.pkeq(403, r.status_code)

    _run_sim(auth_fc, _op)


def test_srw_get_own_jobs(auth_fc):
    from pykern import pkunit
    from pykern.pkdebug import pkdp

    def _op(fc, sim_type):
        r = fc.sr_post(
            'admJobs',
            PKDict(simulationType=sim_type)
        )
        pkunit.pkeq(len(r.rows[0]), len(r.header))
        pkunit.pkeq('srw', r.rows[0][0])

    _run_sim(auth_fc, _op)


def test_srw_user_see_only_own_jobs(auth_fc):
    from pykern import pkunit
    from pykern.pkdebug import pkdp
    import sirepo.auth_db
    import sirepo.auth_role

    def _cancel_job(user, cancel_req):
        _login_as_user(user)
        fc.sr_post('runCancel', cancel_req)

    def _clear_role_db():
        sirepo.auth_db.UserRole.delete_all()

    def _get_jobs(adm, job_count):
        r = fc.sr_post(
            'admJobs' if adm else 'ownJobs',
            PKDict(simulationType=t)
        )
        pkunit.pkeq(job_count, len(r.rows), 'job_count={} len_r={} r={}', len(r.rows), job_count, r)

    def _get_simulation_running():
        d = auth_fc.sr_sim_data(sim_name=n, sim_type='srw')
        r = fc.sr_post(
            'runSimulation',
            PKDict(
                models=d.models,
                report=m,
                simulationId=d.models.simulation.simulationId,
                simulationType=d.simulationType,
            )
        )
        try:
            for _ in range(10):
                if r.state == 'running':
                    return r.nextRequest
                r = fc.sr_post('runStatus', r.nextRequest)
                time.sleep(1)
            else:
                pkunit.pkfail('Never entered running state')
        except Exception:
            fc.sr_post('runCancel', r.nextRequest)
            raise

    def _login_as_user(user):
        fc.sr_logout()
        r = fc.sr_post('authEmailLogin', {'email': user, 'simulationType': t})
        fc.sr_email_confirm(fc, r)

    def _make_user_adm(uid):
        import sirepo.pkcli.roles
        sirepo.pkcli.roles.add_roles(
            uid,
            sirepo.auth_role.ROLE_ADM,
        )
        r = sirepo.auth_db.UserRole.search_all_for_column('uid')
        pkunit.pkeq(1, len(r), 'One user with role adm r={}', r)
        pkunit.pkeq(r[0], uid, 'Expected same uid as user')

    def _register_both_users():
        r = fc.sr_post('authEmailLogin', {'email': adm_user, 'simulationType': t})
        fc.sr_email_confirm(fc, r)
        fc.sr_post('authCompleteRegistration', {'displayName': 'abc', 'simulationType': t},)
        fc.sr_get('authLogout', {'simulation_type': fc.sr_sim_type})
        _make_user_adm(fc.sr_auth_state().uid)
        r = fc.sr_post('authEmailLogin', {'email': non_adm_user, 'simulationType': t})
        fc.sr_email_confirm(fc, r, 'xyz')

    fc = auth_fc
    t = 'srw'
    n = "Young's Double Slit Experiment"
    m = 'multiElectronAnimation'
    adm_user = 'diff@b.c'
    non_adm_user = 'x@y.z'
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
    m = 'multiElectronAnimation'
    t = 'srw'
    c = None

    fc.sr_login_as_guest(sim_type=t)
    d = fc.sr_sim_data(n)
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
        c = r.nextRequest
        for _ in range(10):
            if r.state == 'running':
                op(fc, t)
                return
            r = fc.sr_post('runStatus', r.nextRequest)
            time.sleep(1)
        else:
            pkunit.pkfail('Never entered running state')
    finally:
        fc.sr_post('runCancel', c)
