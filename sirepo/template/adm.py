# -*- coding: utf-8 -*-
u"""Myapp execution template.

:copyright: Copyright (c) 2017-2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp


SIM_TYPE = 'adm'


def get_running_jobs():
    pkdp('xxxxxxxxxxx')
    _get_running_jobs()
    pkdp('xxxxxxxxxxx')

    return PKDict(
        columns=[
            'User id',
            'Sim type',
            'Sim id',
            'Start time',
            'Last update time',
            'Elapsed time',
        ],
        data=[
            ['uid1', 'simType1', 'simId1', 'startTime1', 'lastUpdatTime1', 'elapsedTime1'],
        ]
    )


def _get_running_jobs():
    import sirepo.job_supervisor
    import glob

    for f in glob.glob(sirepo.job_supervisor._DB_DIR):
        pkdp(f)
