# -*- coding: utf-8 -*-
u"""test running of animations through sbatch

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkcollections import PKDict
import pytest


def test_warppba_no_creds(sbatch_animation_fc):
    from pykern.pkunit import pkexcept

    with pkexcept('SRException.*no-creds'):
        sbatch_animation_fc.sr_animation_run(
            sbatch_animation_fc,
            'Laser Pulse',
            'animation',
            PKDict(),
            expect_completed=False,
        )


def test_warppba_invalid_creds(fc, sbatch_animation_fc):
    from pykern.pkunit import pkexcept

    with pkexcept('SRException.*no-creds'):
        sbatch_animation_fc.sr_animation_run(
            sbatch_animation_fc,
            'Laser Pulse',
            'animation',
            PKDict(),
            expect_completed=False,
        )

    data = fc.sr_sim_data('Laser Pulse')
    with pkexcept('SRException.*invalid-creds'):
        fc.sr_post(
            'sbatchLogin',
            PKDict(
                password='bar',
                report=data.report,
                simulationId=data.models.simulation.simulationId,
                simulationType=data.simulationType,
                username='foo',
            )
        )
