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


def test_jspec(fc):
    _r(
        fc,
        'DC Cooling Example',
        'animation',
        PKDict(
            beamEvolutionAnimation=PKDict(
                expect_y_range=r'^.2.04.*e-07, 2.15e-06',
            ),
            coolingRatesAnimation=PKDict(
                expect_y_range=r'-0.04.*, 0.00[4-7]',
            ),
        ),
        timeout=15,
    )


def test_srw(fc):
    _r(
        fc,
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


def test_synergia(fc):
    _r(
        fc,
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
                    '-0.01.*, 0.01.*, 200',
                    '-0.01.*, 0.01.*, 200',
                ][i]
            ),
            turnComparisonAnimation=PKDict(
                 frame_index=0,
                 expect_y_range='^.0.0026.*, 0.0057',
            ),
        ),
    )

def test_warppba(fc):
    _r(
        fc,
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


def test_warpvnd(fc):
    _r(
        fc,
        'Two Poles',
        'fieldCalculationAnimation',
        PKDict(
            fieldCalcAnimation=PKDict(
                expect_y_range='-1e-07, 1e-07, 23',
            ),
        ),
    )
    _r(
        fc,
        'Two Poles',
        'animation',
        PKDict(
            currentAnimation=PKDict(
                expect_y_range='0.0, 3.*e-05',
            ),
            fieldAnimation=PKDict(
                expect_y_range='-1e-07, 1e-07, 23',
            ),
        ),
        expect_completed=False,
        timeout=10,
    )


def test_webcon(fc):
    _r(
        fc,
        'Clustering Demo',
        'epicsServerAnimation',
        PKDict(
            beamPositionReport=PKDict(
                runSimulation=True,
                expect_y_range='^.0.0009.*, 0.09',
            ),
            correctorSettingReport=PKDict(
                runSimulation=True,
                expect_y_range=r'^.0.0, 0.0',
            ),
        ),
        expect_completed=False,
        timeout=10,
    )


def test_zgoubi(fc):
    _r(
        fc,
        'EMMA',
        'animation',
        PKDict(
            bunchAnimation=PKDict(
                expect_title=lambda i: 'Pass {}'.format(i) if i else 'Initial Distribution',
                expect_y_range=lambda i: [
                    '-0.0462.*, -0.0281.*, 200',
                    '-0.0471.*, -0.0283.*, 200',
                    '-0.0472.*, -0.0274.*, 200',
                    '-0.0460.*, -0.0280.*, 200',
                    '-0.0460.*, -0.0294.*, 200',
                    '-0.0473.*, -0.0275.*, 200',
                    '-0.0480.*, -0.0281.*, 200',
                    '-0.0479.*, -0.0299.*, 200',
                    '-0.0481.*, -0.0294.*, 200',
                    '-0.0488.*, -0.0292.*, 200',
                    '-0.0484.*, -0.0303.*, 200',
                ][i],
            ),
        ),
    )


def _r(fc, sim_name, compute_model, reports, **kwargs):
    from pykern import pkconfig
    from pykern import pkunit
    from pykern.pkcollections import PKDict
    from pykern.pkdebug import pkdp, pkdlog
    from sirepo import srunit
    import re
    import time

    data = fc.sr_sim_data(sim_name)
    run = fc.sr_run_sim(data, compute_model, **kwargs)
    for r, a in reports.items():
        if 'runSimulation' in a:
            f = fc.sr_run_sim(data, r)
            for k, v in a.items():
                m = re.search('^expect_(.+)', k)
                if m:
                    pkunit.pkre(
                        v(i) if callable(v) else v,
                        str(f.get(m.group(1))),
                    )
            continue
        if 'frame_index' in a:
            c = [a.get('frame_index')]
        else:
            c = range(run.get(a.get('frame_count_key', 'frameCount')))
            assert c, \
                'frame_count_key={} or frameCount={} is zero'.format(
                    a.get('frame_count_key'), a.get('frameCount'),
                )
        pkdlog('frameReport={} count={}', r, c)
        import sirepo.sim_data

        s = sirepo.sim_data.get_class(fc.sr_sim_type)
        for i in c:
            pkdlog('frameIndex={} frameCount={}', i, run.get('frameCount'))
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
