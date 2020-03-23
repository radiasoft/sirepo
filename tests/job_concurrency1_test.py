# -*- coding: utf-8 -*-
u"""Concurrency testing

This test does not always fail when there is a problem (false
positive), because it depends on a specific sequence of events
that can't be controlled by the test.

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html

"""
from __future__ import absolute_import, division, print_function
import pytest

_REPORT = 'heightWeightReport'


def test_myapp(fc):
    """https://github.com/radiasoft/sirepo/issues/2346"""
    from pykern import pkunit
    import time
    import threading
    from pykern.pkdebug import pkdlog

    d = fc.sr_sim_data()
    d.models.simulation.name = 'srunit_long_run'

    def _t2():
        pkdlog('start 2')
        r2 = fc.sr_post(
            'runSimulation',
            dict(
                forceRun=False,
                models=d.models,
                report=_REPORT,
                simulationId=d.models.simulation.simulationId,
                simulationType=d.simulationType,
            ),
        )
        pkdlog(r2)
        for _ in range(20):
            pkunit.pkok(r2.state != 'error', 'unexpected error state: {}')
            if r2.state == 'running':
                break
            if r2.state == 'canceled':
                pkdlog('canceled')
                break
            time.sleep(.1)
            pkdlog('runStatus 2')
            r2 = fc.sr_post('runStatus', r2.nextRequest)
        else:
            pkunit.pkfail('runStatus: failed to start running: {}', r2)

    pkdlog('start 1')
    r1 = fc.sr_post(
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
        pkdlog(r1)
        pkunit.pkok(r1.state != 'error', 'unexpected error state: {}')
        if r1.state == 'running':
            break
        time.sleep(.1)
        r1 = fc.sr_post('runStatus', r1.nextRequest)
    else:
        pkunit.pkfail('runStatus: failed to start running: {}', r1)

    t2 = threading.Thread(target=_t2)
    t2.start()
    time.sleep(.1)
    pkdlog('runCancel')
    c = fc.sr_post('runCancel', r1.nextRequest)
    pkunit.pkeq('canceled', c.state)

    pkdlog('start 3')
    r1 = fc.sr_post(
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
        pkunit.pkok(r1.state != 'error', 'unexpected error state: {}')
        if r1.state == 'running':
            break
        time.sleep(.1)
        r1 = fc.sr_post('runStatus', r1.nextRequest)
    else:
        pkunit.pkfail('runStatus: failed to start running: {}', r1)
    c = fc.sr_post('runCancel', r1.nextRequest)
    pkunit.pkeq('canceled', c.state)
