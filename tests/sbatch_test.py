# -*- coding: utf-8 -*-
u"""test running of animations through sbatch

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkcollections import PKDict
import os
import pytest


def _slurm_not_installed():
    import subprocess
    try:
        subprocess.check_output(('sbatch', '--help'))
    except OSError:
        return True
    return False


pytestmark = [
    pytest.mark.skipif(
        _slurm_not_installed(),
        reason="slurm not installed, skipping sbatch tests"
    ),
    pytest.mark.skipif(
        not os.environ.get('SIREPO_FEATURE_CONFIG_JOB') == '1',
        reason="SIREPO_FEATURE_CONFIG_JOB != 1"
    ),
]



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


def test_warppba_invalid_creds(fc):
    from pykern import pkunit
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
    from pykern import pkunit
    from pykern.pkunit import pkexcept

    s = 'Laser Pulse'
    c = 'animation'
    data = fc.sr_sim_data(s)
    data.models[c].jobRunMode = 'sbatch'
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
