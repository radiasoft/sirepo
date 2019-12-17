# -*- coding: utf-8 -*-
u"""test cancel of sim

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest


def test_warppba(fc):
    from pykern import pkunit
    from pykern.pkdebug import pkdc, pkdp, pkdlog
    import time

    d = fc.sr_sim_data(sim_name='Laser Pulse', sim_type=fc.sr_sim_type)
    d = fc.sr_post(
        'runSimulation',
        dict(
            forceRun=False,
            models=d.models,
            report='particleAnimation',
            simulationId=d.models.simulation.simulationId,
            simulationType=d.simulationType,
        ),
    )
    for _ in range(10):
        assert d.state != 'error'
        if d.state == 'running':
            break
        time.sleep(d.nextRequestSeconds)
        d = fc.sr_post('runStatus', d.nextRequest)
    else:
        pkunit.pkfail('runStatus: failed to start running: {}', d)
    x = d.nextRequest
    d = fc.sr_post(
        'runCancel',
        x,
    )
    assert d.state == 'canceled'
    d = fc.sr_post(
        'runStatus',
        x,
    )
    assert d.state == 'canceled'
