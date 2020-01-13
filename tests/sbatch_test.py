# -*- coding: utf-8 -*-
u"""test running of animations through sbatch

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkcollections import PKDict
import os
import pytest


pytestmark = pytest.mark.skipif(
    os.environ.get('SIREPO_FEATURE_CONFIG_JOB') != '1',
    reason="SIREPO_FEATURE_CONFIG_JOB != 1"
)


def test_warppba_no_creds(fc):
    from pykern.pkunit import pkexcept

    with pkexcept('SRException.*no-creds'):
        fc.sr_animation_run(
            'Laser Pulse',
            'animation',
            PKDict(),
            expect_completed=False,
        )


def test_warppba_invalid_creds(fc):
    from pykern.pkunit import pkexcept

    c = 'animation'
    data = fc.sr_sim_data('Laser Pulse')
    data.models[c].jobRunMode = 'sbatch'
    with pkexcept('SRException.*no-creds'):
        fc.sr_run_sim(data, c, expect_completed=False)
    with pkexcept('SRException.*invalid-creds'):
        fc.sr_post(
            'sbatchLogin',
            PKDict(
                password='fake pass',
                report=c,
                simulationId=data.models.simulation.simulationId,
                simulationType=data.simulationType,
                username='notarealuser',
            )
        )


def test_warppba_login(fc):
    from pykern.pkunit import pkexcept

    s = 'Laser Pulse'
    c = 'animation'
    data = fc.sr_sim_data(s)
    data.models[c].pkupdate(
        jobRunMode='sbatch',
        sbatchCores=2,
    )
    with pkexcept('SRException.*no-creds'):
        fc.sr_run_sim(data, c, expect_completed=False)
    fc.sr_post(
        'sbatchLogin',
        PKDict(
            password='vagrant',
            report=c,
            simulationId=data.models.simulation.simulationId,
            simulationType=data.simulationType,
            username='vagrant',
        )
    )
    fc.sr_run_sim(data, c, expect_completed=False)
