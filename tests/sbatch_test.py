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
