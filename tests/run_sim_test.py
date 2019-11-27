# -*- coding: utf-8 -*-
u"""test running a simulation

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest

_REPORT = 'heightWeightReport'

def xtest_myapp_runStatus(fc):
    from pykern import pkunit

    d = fc.sr_sim_data()
    r = fc.sr_post(
        'runStatus',
        dict(
            report=_REPORT,
            simulationId=d.models.simulation.simulationId,
            simulationType=d.simulationType,
            computeJobHash='fakeHash',
        ),
    )
    pkunit.pkeq('stopped', r.state)


def test_srw_runCancel(fc):
    from pykern import pkunit
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
    o = subprocess.check_output(['ps', 'axww'], stderr=subprocess.STDOUT)
    o = filter(lambda x: 'mpiexec' in x, o.split('\n'))
    pkunit.pkok(
        not o,
        'found "mpiexec" after cancel in ps={}',
        '\n'.join(o),
    )


def xtest_runSimulation(fc):
    from pykern import pkunit
    from pykern.pkdebug import pkdp, pkdlog
    import time

    d = fc.sr_sim_data()
    r = fc.sr_post(
        'runSimulation',
        dict(
            forceRun=False,
            models=r.models,
            report=_REPORT,
            simulationId=r.models.simulation.simulationId,
            simulationType=r.simulationType,
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
