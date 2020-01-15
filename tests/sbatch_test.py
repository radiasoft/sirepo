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


def xtest_warppba_no_creds(new_user_fc):
    from pykern.pkunit import pkexcept

    c, d = _warppba_login_setup(new_user_fc)
    with pkexcept('SRException.*no-creds'):
        new_user_fc.sr_run_sim(d, c, expect_completed=False)


def xtest_warppba_invalid_creds(new_user_fc):
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


def xtest_warppba_login(new_user_fc):
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


def test_srw_data_file(fc):
    from pykern.pkunit import pkeq

    a = "Young's Double Slit Experiment"
    c = 'multiElectronAnimation'
    fc.sr_animation_run(
        a,
        c,
        PKDict(
            multiElectronAnimation=PKDict(
                # Prevents "Memory Error" because SRW uses computeJobStart as frameCount
                frame_index=0,
                expect_title='E=4240 eV',
            ),
        ),
        expect_completed=False,
        timeout=200,
    )
    d = fc.sr_sim_data(a)
    r = fc.sr_get(
        'downloadDataFile',
        PKDict(
            simulation_type=d.simulationType,
            simulation_id=d.models.simulation.simulationId,
            model=c,
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
