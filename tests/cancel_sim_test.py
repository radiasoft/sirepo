# -*- coding: utf-8 -*-
u"""test cancel of sim

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest


def test_synergia(fc):
    from pykern import pkunit
    from pykern.pkdebug import pkdc, pkdp, pkdlog
    import time

    d = fc.sr_sim_data(sim_name='IOTA 6-6 with NLINSERT', sim_type=fc.sr_sim_type)
    r = fc.sr_post(
        'runSimulation',
        dict(
            forceRun=False,
            models=d.models,
            report='bunchReport1',
            simulationId=d.models.simulation.simulationId,
            simulationType=d.simulationType,
        ),
    )
    for _ in range(20):
        assert r.state != 'error'
        if r.state == 'running':
            break
        time.sleep(.1)
        r = fc.sr_post('runStatus', r.nextRequest)
    else:
        pkunit.pkfail('runStatus: failed to start running: {}', r)
    x = r.nextRequest
    r = fc.sr_post('runCancel', x)
    assert r.state == 'canceled'
    r = fc.sr_post('runStatus', x)
    assert r.state == 'canceled'
    r = fc.sr_post(
        'runSimulation',
        dict(
            forceRun=False,
            models=d.models,
            report='bunchReport1',
            simulationId=d.models.simulation.simulationId,
            simulationType=d.simulationType,
        ),
    )
