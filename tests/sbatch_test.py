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


def test_warppba_no_creds(new_user_fc):
    from pykern.pkunit import pkexcept

    c, d = _warppba_login_setup(new_user_fc)
    with pkexcept('SRException.*no-creds'):
        new_user_fc.sr_run_sim(d, c, expect_completed=False)


def test_warppba_invalid_creds(new_user_fc):
    from pykern.pkunit import pkexcept

    c, d = _warppba_login_setup(new_user_fc)
    with pkexcept('SRException.*no-creds'):
        new_user_fc.sr_run_sim(d, c, expect_completed=False)
    with pkexcept('SRException.*invalid-creds'):
        new_user_fc.sr_post(
            'sbatchLogin',
            PKDict(
                password='fake pass',
                report=c,
                simulationId=d.models.simulation.simulationId,
                simulationType=d.simulationType,
                username='notarealuser',
            )
        )


def test_warppba_login(new_user_fc):
    from pykern.pkunit import pkexcept

    c, d = _warppba_login_setup(new_user_fc)
    with pkexcept('SRException.*no-creds'):
        new_user_fc.sr_run_sim(d, c, expect_completed=False)
    new_user_fc.sr_post(
        'sbatchLogin',
        PKDict(
            password='vagrant',
            report=c,
            simulationId=d.models.simulation.simulationId,
            simulationType=d.simulationType,
            username='vagrant',
        )
    )
    new_user_fc.sr_run_sim(d, c, expect_completed=False)


def test_warppba_data_file(fc):
    from pykern.pkunit import pkeq

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
        expect_completed=False,
    )
    d = fc.sr_sim_data('Laser Pulse')
    r = fc.sr_get(
        'downloadDataFile',
        PKDict(
            simulation_type=d.simulationType,
            simulation_id=d.models.simulation.simulationId,
            model='animation',
            frame='0',
        ),
    )
    pkeq(200, r.status_code)


def _warppba_login_setup(fc):
    c = 'animation'
    d = fc.sr_sim_data('Laser Pulse')
    d.models[c].pkupdate(
        jobRunMode='sbatch',
        sbatchCores=2,
    )
    return c, d
