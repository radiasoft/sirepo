# -*- coding: utf-8 -*-
"""End to end test of running a job.

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest
import os

# TODO(e-carlin): Tests that need to be implemented
#   - agent never starts
#   - agent response is bad (ex no req_id)
#   - server_req is malformed
#   - agent starts but we never get an incoming 'read_for_work' message
#   - canceling of requests in the q and running requests
#   - using only the resources that are available
#   - agent sigterm -> sigkill progression
#   - send kill to uknown agent


_REPORT = 'heightWeightReport'


def test_runCancel(fc):
    from pykern import pkunit
    from pykern.pkdebug import pkdc, pkdp, pkdlog
    import time

    d = fc.sr_sim_data()
    d.models.simulation.name = 'srunit_long_run'
    d = fc.sr_post(
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


def test_runSimulation(fc):
    from pykern import pkunit
    from pykern.pkdebug import pkdp, pkdlog
    from sirepo import job
    import time

    d = fc.sr_sim_data()
    d = fc.sr_post(
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
        pkdlog(d)
        assert d.state != 'error'
        if d.state == 'completed':
            break
        time.sleep(d.nextRequestSeconds)
        d = fc.sr_post('runStatus', d.nextRequest)
    else:
        pkunit.pkfail('runStatus: failed to complete: {}', d)
    # Just double-check it actually worked
    assert u'plots' in d
