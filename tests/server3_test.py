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

    _t(
        'elegant',
        'Compact Storage Ring',
        'animation',
        PKDict({
            'elementAnimation20-18': PKDict(
                expect_y_range='-0.0003.*, 0.0003.*, 200',
            ),
            'elementAnimation20-25': PKDict(
                expect_y_range='^.9.44.*, 0.0012',
            ),
            'elementAnimation22-13': PKDict(
                expect_y_range='-3.78.*e-12, 34.6',
            ),
            'elementAnimation20-3': PKDict(
                expect_x_range='^.0.0, 46.0',
            ),
        })
    )
    _t(
        'jspec',
        'DC Cooling Example',
        'animation',
        PKDict(
            beamEvolutionAnimation=PKDict(
                expect_y_range=r'^.2.04.*e-07, 2.15e-06',
            ),
        ),
    ),
    _t(
        'srw',
        "Young's Double Slit Experiment",
        'multiElectronAnimation',
        PKDict(
            multiElectronAnimation=PKDict(
                # Prevents "Memory Error" because SRW uses computeJobStart as frameCount
                frame_index=0,
                expect_title='E=4240 eV',
            ),
        ),
        expect_completed=False,
    )
    _t(
        'synergia',
        'Simple FODO',
        'animation',
        PKDict(
            beamEvolutionAnimation=PKDict(
                frame_index=7,
                expect_y_range='^.0.00262.*, 0.00572',
            ),
            bunchAnimation=PKDict(
                frame_count_key='bunchAnimation.frameCount',
                expect_title=lambda i: r'turn {}\b'.format(i),
                expect_y_range=lambda i: [
                    '-0.0109.*, 0.011.*, 200',
                    '-0.0108.*, 0.0109.*, 200',
                ][i]
            ),
            turnComparisonAnimation=PKDict(
                 frame_index=0,
                 expect_y_range='^.0.0026.*, 0.0057',
            ),
        ),
    )
    _t(
        'warppba',
        'Laser Pulse',
        'animation',
        PKDict(
            particleAnimation=PKDict(
                expect_title=lambda i: r'iteration {}\)'.format((i + 1) * 50),
                expect_y_range='-2.096.*e-05, 2.096.*e-05, 219',
            ),
            fieldAnimation=PKDict(
                expect_title=lambda i: r'iteration {}\)'.format((i + 1) * 50),
                expect_y_range='-2.064.*e-05, 2.064.*e-05, 66',
            ),
        ),
        expect_completed=False,
    )


def _t(sim_type, sim_name, compute_model, reports, expect_completed=True):
    from pykern.pkcollections import PKDict
    from pykern.pkdebug import pkdp, pkdlog
    from sirepo import srunit
    from pykern import pkunit
    import re
    import sdds
    import time

    data, fc, sim_type = srunit.sim_data(sim_type, sim_name, sim_types=_TYPES)
    cancel = None
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
        cancel = run.nextRequest
        for _ in range(15):
            if run.state in ('completed', 'error'):
                break
            run = fc.sr_post('runStatus', run.nextRequest)
            time.sleep(1)
        else:
            pkunit.pkok(
                not expect_completed,
                'did not complete: runStatus={}',
                run,
            )
        cancel = None
        for r, a in reports.items():
            if 'frame_index' in a:
                c = [a.get('frame_index')]
            else:
                c = range(run.get(a.get('frame_count_key', 'frameCount')))
            pkdlog('report={}', r)
            for i in c:
                pkdlog('frameIndex={}', i)
                f = fc.sr_get_json(
                    'simulationFrame',
                    PKDict(frame_id=s.frame_id(data, run, r, i)),
                )
                for k, v in a.items():
                    m = re.search('^expect_(.+)', k)
                    if m:
                        pkunit.pkre(
                            v(i) if callable(v) else v,
                            str(f.get(m.group(1))),
                        )
    finally:
        try:
            if cancel:
                fc.sr_post('runCancel', cancel)
        except Exception:
            pass
