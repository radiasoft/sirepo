# -*- coding: utf-8 -*-
"""Celery tasks

:copyright: Copyright (c) 2015 Bivio Software, Inc.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkdebug import pkdc, pkdp

import importlib
import os
import sys

from celery import Celery

celery = Celery('sirepo')

celery.conf.update(
    BROKER_URL=os.getenv('SIREPO_CELERY_TASKS_BROKER_URL', 'amqp://guest@localhost//'),
    CELERYD_CONCURRENCY=os.getenv('SIREPO_CELERY_TASKS_CELERYD_CONCURRENCY', 1),
    CELERYD_LOG_COLOR=False,
    CELERYD_PREFETCH_MULTIPLIER=1,
    CELERYD_TASK_TIME_LIMIT=3600,
    CELERY_ACKS_LATE=True,
    CELERY_RESULT_BACKEND = 'rpc',
    CELERY_RESULT_PERSISTENT=True,
    CELERY_TASK_PUBLISH_RETRY=False,
    CELERY_TASK_RESULT_EXPIRES=None,
    CELERYD_MAX_TASKS_PER_CHILD=1,
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
    sys.argv[:] = ['simulation_type']
    importlib.import_module('sirepo.pykern_cli.' + simulation_type).run_background(run_dir)
    # Doesn't return anything
