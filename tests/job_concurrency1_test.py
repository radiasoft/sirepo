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



def test_myapp_cancel(fc):
    """https://github.com/radiasoft/sirepo/issues/2346"""
    from pykern import pkunit
    import time
    import threading
    from pykern.pkdebug import pkdlog

    d = fc.sr_sim_data()
    d.models.simulation.name = 'srunit_long_run'
    r = 'heightWeightReport'

    def _t2():
        pkdlog('start 2')
        r2 = fc.sr_post(
            'runSimulation',
            dict(
                forceRun=False,
                models=d.models,
                report=r,
                simulationId=d.models.simulation.simulationId,
                simulationType=d.simulationType,),)
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
            report=r,
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
            report=r,
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


def test_elegant_concurrent_sim_frame(fc):
    """https://github.com/radiasoft/sirepo/issues/2474"""
    from pykern import pkunit
    from pykern.pkcollections import PKDict
    from pykern.pkdebug import pkdlog, pkdp
    import sirepo.sim_data
    import threading
    import time
    def _get_frames():
        for i in range(3):
            f = fc.sr_get_json(
                'simulationFrame',
                PKDict(frame_id=s.frame_id(d, r1, 'elementAnimation19-5', 0)),
            )
            pkunit.pkeq('completed', f.state)

    def _t2(get_frames):
        get_frames()

    d = fc.sr_sim_data(sim_name='Backtracking', sim_type='elegant' )
    s = sirepo.sim_data.get_class(fc.sr_sim_type)
    r = 'animation'
    r1 = PKDict()
    try:
        pkdlog('start 1')
        r1 = fc.sr_post(
            'runSimulation',
            dict(
                forceRun=False,
                models=d.models,
                report=r,
                simulationId=d.models.simulation.simulationId,
                simulationType=d.simulationType,
            ),
        )
        for _ in range(10):
            pkunit.pkok(r1.state != 'error', 'unexpected error state: {}')
            if r1.state == 'completed':
                break
            time.sleep(1)
            r1 = fc.sr_post('runStatus', r1.nextRequest)
        else:
            pkunit.pkfail('runStatus: failed to complete: {}', r1)
        t2 = threading.Thread(target=_t2, args=(_get_frames,))
        t2.start()
        _get_frames()
        t2.join()
    finally:
        if r1.get('nextRequest'):
            fc.sr_post('runCancel', r1.nextRequest)
