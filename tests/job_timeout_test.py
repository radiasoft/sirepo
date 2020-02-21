# -*- coding: utf-8 -*-
u"""test for canceling a long running simulation due to a timeout

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkcollections import PKDict
import os
import pytest


def setup_module(module):
    os.environ.update(
        SIREPO_JOB_SUPERVISOR_MAX_HOURS_PARALLEL='0.002',
        SIREPO_JOB_SUPERVISOR_MAX_HOURS_ANALYSIS='0.001',
        SIREPO_FEATURE_CONFIG_JOB='1',
    )


def test_srw(fc):
    from pykern import pkunit
    from pykern.pkdebug import pkdlog, pkdexc
    import time
    m = 'multiElectronAnimation'
    data = fc.sr_sim_data("Young's Double Slit Experiment")
    try:
        r = fc.sr_post(
            'runSimulation',
            PKDict(
                models=data.models,
                report=m,
                simulationId=data.models.simulation.simulationId,
                simulationType=data.simulationType,
            ),
        )
        if r.state == 'completed':
            return r
        cancel = r.get('nextRequest')
        for _ in range(10):
            if r.state == 'canceled':
                cancel = None
                break
            r = fc.sr_post('runStatus', r.nextRequest)
            time.sleep(1)
        else:
            pkunit.pkfail('did not cancel in time')
    finally:
        if cancel:
            fc.sr_post('runCancel', cancel)
        import subprocess
        o = subprocess.check_output(['ps', 'axww'], stderr=subprocess.STDOUT)
        o = filter(lambda x: 'mpiexec' in x, o.split('\n'))
        if o:
            pkdlog('found "mpiexec" after cancel in ps={}', '\n'.join(o))
            raise AssertionError('cancel failed')


def test_myapp_analysis(fc):
    from pykern import pkunit
    from pykern.pkdebug import pkdp

    d = fc.sr_sim_data()
    r = fc.sr_run_sim(d, 'heightWeightReport', expect_completed=True)
    r = fc.sr_get(
        'downloadDataFile',
        PKDict(
            simulation_type=d.simulationType,
            simulation_id=d.models.simulation.simulationId,
            model='heightWeightReport',
            frame='-1',
            suffix='sr_long_analysis',
        ),
    )
    pkunit.pkok(r.status_code == 404, 'r={}', r)
