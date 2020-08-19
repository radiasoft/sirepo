# -*- coding: utf-8 -*-
u"""test cancel of sim with agent_start_delay

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest

_REPORT = 'heightWeightReport'


def test_myapp(fc):
    from pykern import pkunit
    from pykern.pkdebug import pkdc, pkdp, pkdlog
    import threading
    import time

    d = fc.sr_sim_data()
    d.models.dog.favoriteTreat = 'agent_start_delay=5'
    x = dict(
        forceRun=False,
        models=d.models,
        report=_REPORT,
        simulationId=d.models.simulation.simulationId,
        simulationType=d.simulationType,
    )
    t1 = threading.Thread(target=lambda: fc.sr_post('runSimulation', x))
    t1.start()
    time.sleep(1)
    t2 = threading.Thread(target=lambda: fc.sr_post('runCancel', x))
    t2.start()
    time.sleep(1)
    r = fc.sr_run_sim(d, _REPORT)
    pkdp('abc')
    p = r.get('plots')
    pkunit.pkok(p, 'expecting truthy r.plots={}', p)
