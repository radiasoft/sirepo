# -*- coding: utf-8 -*-
u"""animations that read data dynamically

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest


def test_synergia(fc):
    from pykern.pkcollections import PKDict
    from pykern.pkdebug import pkdp
    from pykern.pkunit import pkre
    import sirepo.sim_data
    import time

    data = fc.sr_sim_data('IOTA 6-6 with NL Element')
    cancel = None
    # this seems to provoke the error better
#    data.models.simulationSettings.space_charge = '2d-bassetti_erskine'
    s = sirepo.sim_data.get_class(fc.sr_sim_type)
    try:
        r = fc.sr_post(
            'runSimulation',
            PKDict(
                forceRun=True,
                models=data.models,
                report='animation',
                simulationId=data.models.simulation.simulationId,
                simulationType=data.simulationType,
            ),
        )
        cancel = r.nextRequest
        for _ in range(100):
            if r.state in ('completed', 'error'):
                pkdp(r.state)
                cancel = None
                break
            r = fc.sr_post('runStatus', r.nextRequest)
            if r.frameCount > 0:
                for i in range(r.frameCount, r.frameCount - 5, -1):
                    f = fc.sr_get_json(
                        'simulationFrame',
                        PKDict(frame_id=s.frame_id(data, r, 'beamEvolutionAnimation', r.frameCount - i)),
                    )
                    if f.get('error'):
                        pkdp(f.error)
                        pkre('not generated', f.error)
                        # cannot guarantee this happens, but exit if it does
                        break
            time.sleep(0.1)
    finally:
        try:
            if cancel:
                fc.sr_post('runCancel', cancel)
        except Exception:
            pass
    assert 0
