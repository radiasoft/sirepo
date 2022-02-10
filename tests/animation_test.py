# -*- coding: utf-8 -*-
u"""Test background processes

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkcollections import PKDict
import pytest

def test_controls(fc):
    fc.sr_animation_run(
        fc.sr_sim_data('Sample MAD-X beamline'),
        'animation',
        PKDict(),
        expect_completed=False,
    )


def test_elegant(fc):
    import sirepo.template.lattice
    data = fc.sr_sim_data('Compact Storage Ring')
    sirepo.template.lattice.LatticeUtil.find_first_command(data, 'bunched_beam').n_particles_per_bunch = 1
    fc.sr_animation_run(
        data,
        'animation',
        PKDict({
            'elementAnimation22-13': PKDict(
                expect_x_range='0.0, 46',
                expect_y_range='-1.*e-15, 34.6',
            ),
        }),
        timeout=30,
    )


def test_jspec(fc):
    data = fc.sr_sim_data('DC Cooling Example')
    data.models.simulationSettings.update(dict(
        time=1,
        step_number=1,
        time_step=1,
    ))
    fc.sr_animation_run(
        data,
        'animation',
        PKDict(
            #TODO(robnagler) these are sometimes off, just rerun
            beamEvolutionAnimation=PKDict(
                expect_y_range=r'2.15e-06',
            ),
            coolingRatesAnimation=PKDict(
                expect_x_range=r'0, 1\.0',
            ),
        ),
        timeout=20,
    )


def test_madx(fc):
    import sirepo.template.lattice
    data = fc.sr_sim_data('FODO PTC')
    sirepo.template.lattice.LatticeUtil.find_first_command(data, 'beam').npart = 1
    fc.sr_animation_run(
        data,
        'animation',
        PKDict(),
    )


def test_ml(fc):
    fc.sr_animation_run(
        fc.sr_sim_data('iris Dataset'),
        'animation',
        PKDict(),
        timeout=45,
    )


def test_opal(fc):
    fc.sr_animation_run(
        fc.sr_sim_data('CSR Bend Drift'),
        'animation',
        PKDict(),
    )


def test_radia(fc):
    fc.sr_animation_run(
        fc.sr_sim_data('Dipole'),
        'solverAnimation',
        PKDict(),
    )


def test_srw(fc):
    data = fc.sr_sim_data("Young's Double Slit Experiment")
    data.models.multiElectronAnimation.numberOfMacroElectrons = 4
    data.models.simulation.sampleFactor = 0.0001
    fc.sr_animation_run(
        data,
        'multiElectronAnimation',
        PKDict(
            multiElectronAnimation=PKDict(
                # Prevents "Memory Error" because SRW uses computeJobStart as frameCount
                frame_index=0,
                expect_title='E=4240 eV',
            ),
        ),
        timeout=20,
    )


def test_synergia(fc):
    fc.sr_animation_run(
        fc.sr_sim_data('Simple FODO'),
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
    data = fc.sr_sim_data('Laser Pulse')
    data.models.simulationGrid.update(dict(
        rScale=1,
        rLength=5.081245038595,
        rMax=5.081245038595,
        rMin=0,
        rCount=8,
        rCellsPerSpotSize=8,
        rParticlesPerCell=1,
        rCellResolution=20,
        zScale=1,
        zLength=10.162490077316,
        zMax=1.6,
        zMin=-10.162490077316,
        zCellsPerWavelength=8,
        zCount=118,
        zParticlesPerCell=1,
        zCellResolution=20,
    ))
    data.models.electronPlasma.length = 0.05
    fc.sr_animation_run(
        data,
        'animation',
        PKDict(
            particleAnimation=PKDict(
                expect_title=lambda i: r'iteration {}\)'.format((i + 1) * 50),
                expect_y_range='-5.7.*e-06, 5.7.*e-06, 219',
            ),
            fieldAnimation=PKDict(
                expect_title=lambda i: r'iteration {}\)'.format((i + 1) * 50),
                expect_y_range='-5.*e-06, 5.*e-06, 18',
            ),
        ),
        timeout=20,
    )


def test_warpvnd(fc):
    fc.sr_animation_run(
        fc.sr_sim_data('Two Poles'),
        'fieldCalculationAnimation',
        PKDict(
            fieldCalcAnimation=PKDict(
                frame_index=0,
                expect_y_range='-1e-07, 1e-07, 23',
            ),
        ),
        timeout=20,
    )
    data = fc.sr_sim_data('Two Poles')
    data.models.simulationGrid.update(dict(
        num_steps=100,
        channel_width=0.09,
    ))
    fc.sr_animation_run(
        data,
        'animation',
        PKDict(
            currentAnimation=PKDict(
                frame_index=0,
                expect_y_range='0.0, 9.9.*e-06',
            ),
            fieldAnimation=PKDict(
                frame_index=0,
                expect_y_range='-4.5e-08, 4.5e-08, 23',
            ),
        ),
        timeout=20,
    )


def test_zgoubi(fc):
    fc.sr_animation_run(
        fc.sr_sim_data('EMMA'),
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
