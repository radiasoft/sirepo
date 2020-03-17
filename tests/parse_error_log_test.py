# -*- coding: utf-8 -*-
"""Parsing of an error run.log

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest
import os

def test_runError(fc):
    from pykern import pkunit
    from pykern.pkdebug import pkdc, pkdp, pkdlog
    import time

    d = fc.sr_sim_data()
    d.models.simulation.name = 'srunit_error_run'
    d = fc.sr_post(
        'runSimulation',
        dict(
            forceRun=False,
            models=d.models,
            report='heightWeightReport',
            simulationId=d.models.simulation.simulationId,
            simulationType=d.simulationType,
        ),
    )
    for _ in range(10):
        if d.state == 'error':
            pkunit.pkeq("raise AssertionError('a big ugly error')", d.error)
            return
        time.sleep(d.nextRequestSeconds)
        d = fc.sr_post('runStatus', d.nextRequest)
    else:
        pkunit.pkfail('Error never returned d={}', d)
