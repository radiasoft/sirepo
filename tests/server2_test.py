# -*- coding: utf-8 -*-
u"""more server tests

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
import pytest


def test_user_alert():
    from pykern.pkunit import pkeq, pkre
    from sirepo import srunit

    fc, l = srunit.init_auth_db()
    x = l[0].simulation
    d = fc.sr_get_json(
        'simulationData',
        params=dict(
            pretty='1',
            simulation_id=x.simulationId,
            simulation_type='myapp',
        ),
    )
    d.models.dog.breed = 'user_alert=user visible text'
    r = fc.sr_post(
        'runSimulation',
        PKDict(
            forceRun=False,
            models=d.models,
            report='heightWeightReport',
            simulationId=d.models.simulation.simulationId,
            simulationType=d.simulationType,
        ),
    )
    pkdp(r)
    pkeq('error', r.state)
    pkeq('user visible text', r.error)
