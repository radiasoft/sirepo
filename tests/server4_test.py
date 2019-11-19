# -*- coding: utf-8 -*-
u"""Test background processes

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkcollections import PKDict
import pytest


def test_elegant(fc):
    _r(
        fc,
        'Compact Storage Ring',
        'twissReport',
    )


def test_synergia(fc):
    _r(
        fc,
        'Simple FODO',
        'bunchReport1',
        shared_model='bunchReport2',
    )


def test_warppba(fc):
    _r(
        fc,
        'Electron Beam',
        'beamPreviewReport',
    )
    _r(
        fc,
        'Laser Pulse',
        'laserPreviewReport',
    )


def test_zgoubi(fc):
    _r(
        fc,
        'Los Alamos Proton Storage Ring',
        'beamPreviewReport',
    )
    _r(
        fc,
        'Laser Pulse',
        'laserPreviewReport',
    )


def _r(fc, sim_name, analysis_model, shared_model=None):
    from pykern.pkdebug import pkdp, pkdlog
    from sirepo import srunit
    from pykern import pkunit
    import re
    import time

    data = fc.sr_sim_data(sim_name)
    cancel = None
    try:
        run = fc.sr_post(
            'runSimulation',
            PKDict(
                forceRun=False,
                models=data.models,
                report=analysis_model,
                simulationId=data.models.simulation.simulationId,
                simulationType=data.simulationType,
            ),
        )
        import sirepo.sim_data

        s = sirepo.sim_data.get_class(fc.sr_sim_type)
        pkunit.pkeq('pending', run.state, 'not pending, run={}', run)
        cancel = next_request = run.nextRequest
        for _ in range(7):
            if run.state in ('completed', 'error'):
                cancel = None
                break
            run = fc.sr_post('runStatus', run.nextRequest)
            time.sleep(1)
        else:
            pkunit.pkfail('did not complete: runStatus={}', run)
        pkunit.pkeq('completed', run.state)

        if shared_model:
            next_request.report = shared_model
            run = fc.sr_post('runStatus', next_request)
            pkunit.pkeq('completed',  run.state)

    finally:
        try:
            if cancel:
                fc.sr_post('runCancel', cancel)
        except Exception:
            pass
