# -*- coding: utf-8 -*-
u"""Concurrency testing

This test does not always fail when there is a problem (false
positive), because it depends on a specific sequence of events
that can't be controlled by the test.

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html

"""
import pytest

import sirepo.util

def setup_module(module):
    import os
    os.environ.update(
        SIREPO_JOB_DRIVER_LOCAL_SLOTS_PARALLEL='1',
        SIREPO_JOB_DRIVER_LOCAL_SLOTS_SEQUENTIAL='1'
    )


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
    for _ in range(50):
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


def test_srw_io(fc):
    import time
    import threading
    from pykern import pkunit
    from pykern.pkdebug import pkdlog
    from pykern.pkcollections import PKDict
    from sirepo import srunit

    #fc = srunit.flask_client(
    #    cfg={
    #        'SIREPO_FEATURE_CONFIG_SIM_TYPES': 'srw',
    #        'SIREPO_JOB_DRIVER_LOCAL_SLOTS_PARALLEL': '4',
    #    }
    #)
    #d = fc.sr_sim_data(sim_name='NSLS-II TES beamline', sim_type='srw')
    d = fc.sr_sim_data('NSLS-II TES beamline')
    reports = ['beamlineAnimation', 'coherentModesAnimation']
    num_runs = len(reports)
    runs = []
    for _ in range(num_runs + 1):
        runs.append(PKDict(res={}, done=False))

    def _monitor_run(i):
        r = runs[i]
        for _ in range(100):
            time.sleep(.1)
            if r.done:
                fc.sr_post('runCancel', r.res.nextRequest)
                break
            r.res = fc.sr_post('runStatus', r.res.nextRequest)

    def _start_run(i):
        r = runs[i]
        r.res = fc.sr_post(
            'runSimulation',
            PKDict(
                forceRun=False,
                models=d.models,
                report=reports[i],
                simulationId=d.models.simulation.simulationId,
                simulationType=d.simulationType,
            ),
        )
        for _ in range(50):
            pkunit.pkok(r.res.state != 'error', 'unexpected error state: {}')
            if r.res.state == 'pending' or r.res.state == 'running':
                break
            time.sleep(.1)
            r.res = fc.sr_post('runStatus', r.res.nextRequest)
        else:
            pkunit.pkfail('runStatus: failed to start running: {}', r.res)
        threading.Thread(target=_get_t(i + 1)).start()
        _monitor_run(i)
        time.sleep(.1)

    def _tn():
        try:
            runs[num_runs].res = fc.sr_get(
                'downloadDataFile',
                PKDict(
                    simulation_type=d.simulationType,
                    simulation_id=d.models.simulation.simulationId,
                    model=reports[0],
                    frame='0',
                    suffix='dat',
                ),
            )
        except Exception as e:
            runs[num_runs].res = str(e)
        for r in runs:
            r.done = True
        time.sleep(1)

    def _get_t(i):
        if i < num_runs:
            return lambda: _start_run(i)
        return _tn

    _get_t(0)()

    pkdlog('** FINAL {} **', runs)
    s = runs[num_runs - 1].res.state
    pkunit.pkok(s == 'pending', 'unexpected run state: {}', s)


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
