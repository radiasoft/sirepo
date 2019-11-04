# -*- coding: utf-8 -*-
u"""Test background processes

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest

_TYPES = 'warppba'


def test_warpbpa():
    from pykern.pkcollections import PKDict
    from pykern.pkdebug import pkdp
    from sirepo import srunit
    from pykern import pkunit
    import time
    import sdds

    data, fc, sim_type = srunit.sim_data('warppba', 'Electron Beam', sim_types=_TYPES)
    run = fc.sr_post(
        'runSimulation',
        PKDict(
            forceRun=False,
            models=data.models,
            report='animation',
            simulationId=data.models.simulation.simulationId,
            simulationType=data.simulationType,
        ),
    )
    import sirepo.sim_data

    s = sirepo.sim_data.get_class(sim_type)
    pkunit.pkeq('pending', run.state, 'not pending, run={}', run)
    for _ in range(10):
        if run.frameCount >= 1:
            break
        run = fc.sr_post(
            'runStatus',
            run.nextRequest
        )
        time.sleep(1)
    else:
        pkunit.pkfail('runStatus: failed to complete: {}', run)

    f = fc.sr_get_json(
        'simulationFrame',
        PKDict(
            frame_id=s.frame_id(data, run, 'beamAnimation', 0),
        ),
    )
    pkunit.pkre('t = .*iteration', f.title)
