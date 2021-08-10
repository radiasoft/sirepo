# -*- coding: utf-8 -*-
u"""Test background processes

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkcollections import PKDict
import pytest


def test_elegant(fc):
    fc.sr_animation_run(
        'bunchComp - fourDipoleCSR',
        'animation',
        PKDict({
            'elementAnimation13-5': PKDict(
                expect_x_range='3.9.*, 3.9.*, 200',
            ),
        }),
        timeout=30,
    )
    fc.sr_animation_run(
        'Compact Storage Ring',
        'animation',
        PKDict({
            'elementAnimation20-21': PKDict(
                expect_y_range='-0.0003.*, 0.0003.*, 200',
            ),
            'elementAnimation20-29': PKDict(
                expect_y_range='^.9.44.*, 0.0012',
            ),
            'elementAnimation22-13': PKDict(
                expect_y_range=', 34.6',
            ),
            'elementAnimation20-4': PKDict(
                expect_x_range='^.0.0, 46.0',
            ),
        }),
    )


def test_jspec(fc):
    fc.sr_animation_run(
        'DC Cooling Example',
        'animation',
        PKDict(
            #TODO(robnagler) these are sometimes off, just rerun
            beamEvolutionAnimation=PKDict(
                expect_y_range=r'2.15e-06',
            ),
            coolingRatesAnimation=PKDict(
                expect_y_range=r'-[\d\.]+, (0.00|0)\b',
            ),
        ),
        timeout=20,
    )


def test_srw(fc):
    fc.sr_animation_run(
        "Young's Double Slit Experiment",
        'multiElectronAnimation',
        PKDict(
            multiElectronAnimation=PKDict(
                # Prevents "Memory Error" because SRW uses computeJobStart as frameCount
                frame_index=0,
                expect_title='E=4240 eV',
            ),
        ),
        timeout=20,
        expect_completed=False,
    )


def test_synergia(fc):
    fc.sr_animation_run(
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
    fc.sr_animation_run(
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
        timeout=20,
        expect_completed=False,
    )


def test_warpvnd_1(fc):
    fc.sr_animation_run(
        'Two Poles',
        'fieldCalculationAnimation',
        PKDict(
            fieldCalcAnimation=PKDict(
                frame_index=0,
                expect_y_range='-1e-07, 1e-07, 23',
            ),
        ),
        timeout=20,
    )


def test_warpvnd_2(fc):
    fc.sr_animation_run(
        'Two Poles',
        'animation',
        PKDict(
            currentAnimation=PKDict(
                frame_index=0,
                expect_y_range='0.0, 2.*e-05',
            ),
            fieldAnimation=PKDict(
                frame_index=0,
                expect_y_range='-1e-07, 1e-07, 23',
            ),
        ),
        expect_completed=False,
        timeout=20,
    )


def test_zgoubi(fc):
    fc.sr_animation_run(
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
