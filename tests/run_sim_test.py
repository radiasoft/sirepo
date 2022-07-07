# -*- coding: utf-8 -*-
u"""test running a simulation

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest

_REPORT = 'heightWeightReport'


def test_myapp_status(fc):
    from pykern import pkunit
    import os
    import sirepo.feature_config

    d = fc.sr_sim_data()
    r = fc.sr_post(
        'runStatus',
        dict(
            computeJobHash='fakeHash',
            models=d.models,
            report=_REPORT,
            simulationId=d.models.simulation.simulationId,
            simulationType=d.simulationType,
        ),
    )
    pkunit.pkeq('missing', r.state)


def test_myapp_cancel_error(fc):
    from pykern import pkunit
    import time

    d = fc.sr_sim_data()
    d.models.simulation.name = 'srunit_long_run'
    r = fc.sr_post(
        'runSimulation',
        dict(
            forceRun=False,
            models=d.models,
            report=_REPORT,
            simulationId=d.models.simulation.simulationId,
            simulationType=d.simulationType,
        ),
    )
    for _ in range(10):
        pkunit.pkok(r.state != 'error', 'unexpected error state: {}')
        if r.state == 'running':
            break
        time.sleep(r.nextRequestSeconds)
        r = fc.sr_post('runStatus', r.nextRequest)
    else:
        pkunit.pkfail('runStatus: failed to start running: {}', r)
    x = r.nextRequest
    x.simulationType = 'nosuchtype'
    r = fc.sr_post('runCancel', x)
    pkunit.pkeq('canceled', r.state)
    x.simulationType = d.simulationType
    r = fc.sr_post('runStatus', x)
    pkunit.pkeq('running', r.state)
    r = fc.sr_post('runCancel', x)
    pkunit.pkeq('canceled', r.state)
    r = fc.sr_post('runStatus', x)
    pkunit.pkeq('canceled', r.state)


def test_myapp_sim(fc):
    from pykern import pkunit
    from pykern.pkdebug import pkdp, pkdlog
    import time

    d = fc.sr_sim_data()
    r = fc.sr_post(
        'runSimulation',
        dict(
            forceRun=False,
            models=d.models,
            report=_REPORT,
            simulationId=d.models.simulation.simulationId,
            simulationType=d.simulationType,
        ),
    )
    for _ in range(10):
        pkdlog(r)
        pkunit.pkok(r.state != 'error', 'expected error state: {}')
        if r.state == 'completed':
            break
        time.sleep(r.nextRequestSeconds)
        r = fc.sr_post('runStatus', r.nextRequest)
    else:
        pkunit.pkfail('runStatus: failed to complete: {}', r)
    # Just double-check it actually worked
    pkunit.pkok(u'plots' in r, '"plots" not in response={}', r)


def test_srw_cancel(fc):
    from pykern import pkunit, pkcompat
    import subprocess
    import time

    d = fc.sr_sim_data("Young's Double Slit Experiment", sim_type='srw')
    r = fc.sr_post(
        'runSimulation',
        dict(
            forceRun=False,
            models=d.models,
            report='multiElectronAnimation',
            simulationId=d.models.simulation.simulationId,
            simulationType=d.simulationType,
        ),
    )
    for _ in range(10):
        pkunit.pkok(r.state != 'error', 'expected error state: {}')
        if r.state == 'running':
            break
        time.sleep(r.nextRequestSeconds)
        r = fc.sr_post('runStatus', r.nextRequest)
    else:
        pkunit.pkfail('runStatus: failed to start running: {}', r)
    x = r.nextRequest
    r = fc.sr_post('runCancel', x)
    pkunit.pkeq('canceled', r.state)
    r = fc.sr_post('runStatus', x)
    pkunit.pkeq('canceled', r.state)
    o = pkcompat.from_bytes(
        subprocess.check_output(['ps', 'axww'], stderr=subprocess.STDOUT),
    )
    o = list(filter(lambda x: 'mpiexec' in x, o.split('\n')))
    pkunit.pkok(
        not o,
        'found "mpiexec" after cancel in ps={}',
        '\n'.join(o),
    )
