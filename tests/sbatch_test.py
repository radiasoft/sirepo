# -*- coding: utf-8 -*-
u"""test running of animations through sbatch

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp
import pytest


def setup_module(module):
    import os
    import pykern.pkio
    import re

    h = 'v.radia.run'
    k = pykern.pkio.py_path('/home/vagrant/.ssh/known_hosts').read()
    m = re.search('^{}.*$'.format(h), k, re.MULTILINE)
    assert m, \
        'You need to ssh into {} to get the host key'.format(h)

    e = os.environ
    e.update(
        PYENV_VERSION='py3',
        PYTHONUNBUFFERED='1',
        SIREPO_JOB_DRIVER_MODULES='local:sbatch',
        SIREPO_JOB_DRIVER_SBATCH_HOST=h,
        SIREPO_JOB_DRIVER_SBATCH_HOST_KEY=m.group(0),
        SIREPO_JOB_DRIVER_SBATCH_SIREPO_CMD='$HOME/.pyenv/versions/py3/bin/sirepo',
        SIREPO_JOB_DRIVER_SBATCH_SRDB_ROOT='/var/tmp/{sbatch_user}/sirepo',
        SIREPO_SIMULATION_DB_SBATCH_DISPLAY='testing@123'
    )


def test_warppba(animation_fc):
    from pykern.pkunit import pkexcept

    with pkexcept('SRException.*no-creds'):
        animation_fc.sr_animation_run(
            animation_fc,
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
