# -*- coding: utf-8 -*-
"""Celery tasks

:copyright: Copyright (c) 2015 Bivio Software, Inc.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkconfig
pkconfig.append_load_path('sirepo')

import importlib
import os
import sys

from pykern.pkdebug import pkdc, pkdp
from pykern import pkcollections

from celery import Celery

celery = Celery('sirepo')

cfg = pkconfig.init(
    broker_url=('amqp://guest@localhost//', str, 'Celery: queue broker url'),
    celeryd_concurrency=(1, int, 'how many tasks to run in parallel'),
    celeryd_task_time_limit=(3600, int, 'max run time for a task in seconds'),
)

celery.conf.update(
    pkcollections.map_items(cfg, op=lambda k, v: (k.upper(), v)),
)

celery.conf.update(
    CELERYD_LOG_COLOR=False,
    CELERYD_MAX_TASKS_PER_CHILD=1,
    CELERYD_PREFETCH_MULTIPLIER=1,
    CELERYD_TASK_SOFT_TIME_LIMIT=celery.conf['CELERYD_TASK_TIME_LIMIT'] - 10,
    CELERY_ACKS_LATE=True,
    CELERY_RESULT_BACKEND = 'rpc',
    CELERY_RESULT_PERSISTENT=True,
    CELERY_TASK_PUBLISH_RETRY=False,
    CELERY_TASK_RESULT_EXPIRES=None,
)

@celery.task
def start_simulation(simulation_type, run_dir):
    """Call simulation's in run_background with run_dir

    Args:
        simulation_type (str): currently must be warp
        run_dir (py.path.local): directory
    """
    # [2016-01-27 13:59:54,133: WARNING/Worker-1] celery: error: no such option: -A
    # srw_bl.py assumes it can parse sys.argv so we have to clear sys.argv
    sys.argv[:] = [simulation_type]
    importlib.import_module('sirepo.pkcli.' + simulation_type).run_background(run_dir)
    # Doesn't return anything
