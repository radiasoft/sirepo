# -*- coding: utf-8 -*-
u"""Myapp execution template.

:copyright: Copyright (c) 2017-2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp
import sirepo.job
import pykern.pkjson
import datetime


SIM_TYPE = 'adm'


def get_running_jobs():
    return PKDict(
        columns=[
            'User id',
            'Simulation type',
            'Simulation id',
            'Start time (UTC)',
            'Last update time (UTC)',
            'Elapsed time',
        ],
        data=_get_running_jobs(),
    )


def _get_running_jobs():
    def _strftime(epoch):
        return datetime.datetime.utcfromtimestamp(
            int(epoch),
        ).strftime('%Y-%m-%d %H:%M:%S')

    o = []
    for f in sirepo.job.SUPERVISOR_DB_DIR.listdir(sort=True):
        d = pykern.pkjson.load_any(f)
        if d.status == sirepo.job.RUNNING:
            s = int(d.computeJobStart)
            l = int(d.lastUpdateTime)
            o.append(
                [
                    d.uid,
                    d.simulationType,
                    d.simulationId,
                    _strftime(s),
                    _strftime(l),
                    l - s,
                ],
            )
    return o
