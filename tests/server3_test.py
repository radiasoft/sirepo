# -*- coding: utf-8 -*-
u"""Test background processes

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest


_TYPES = 'elegant:jspec:srw:synergia:warppba:warpvnd:webcon:zgoubi'


def test_simulation_frame():
    from pykern.pkcollections import PKDict

#TODO(robnagler) add more reports
#    _t('elegant', 'Compact Storage Ring', 'animation', 'elementAnimation20-18', title='Horizontal')
#    _t('jspec', 'Booster Ring', 'animation', 'beamEvolutionAnimation', x_label='t .s.')
#    _t('srw', "Young's Double Slit Experiment", 'multiElectronAnimation', 'multiElectronAnimation', title='E=4240 eV')
    _t(
        'synergia',
        'Simple FODO',
        'animation',
        bunchAnimation=PKDict(title='x-y at 0.0m, turn 0'),
    ),
#    _t('warppba', 'Electron Beam', 'animation', 'beamAnimation', title='t = .*iteration')


def _t(sim_type, sim_name, compute_model, **reports):
    from pykern.pkcollections import PKDict
    from pykern.pkdebug import pkdp
    from sirepo import srunit
    from pykern import pkunit
    import time
    import sdds

    data, fc, sim_type = srunit.sim_data(sim_type, sim_name, sim_types=_TYPES)
    run = None
    try:
        run = fc.sr_post(
            'runSimulation',
            PKDict(
                forceRun=True,
                models=data.models,
                report=compute_model,
                simulationId=data.models.simulation.simulationId,
                simulationType=data.simulationType,
            ),
        )
        import sirepo.sim_data

        s = sirepo.sim_data.get_class(sim_type)
        pkunit.pkeq('pending', run.state, 'not pending, run={}', run)
        for _ in range(10):
#TODO(robnagler) completed or run frameCount
            if run.state == ('completed', 'error'):
                break
            if run.frameCount >= 8:
                break
            run = fc.sr_post('runStatus', run.nextRequest)
            time.sleep(1)
        else:
            pkunit.pkfail('runStatus: failed to complete: {}', run)
        r = 'bunchAnimation'
        for i in range(run['bunchAnimation.frameCount']):
            f = fc.sr_get_json(
                'simulationFrame',
                PKDict(frame_id=s.frame_id(data, run, r, i)),
            )
            pkdp(f.title)

        return
        for r, t in reports.items():
            f = fc.sr_get_json(
                'simulationFrame',
                PKDict(frame_id=s.frame_id(data, run, r, 8)),
            )
            for k, v in t.items():
                pkunit.pkre(v, f.get(k))
    finally:
        try:
            if run:
                fc.sr_post('runCancel', run.nextRequest)
        except Exception:
            pass
