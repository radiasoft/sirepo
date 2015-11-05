# -*- coding: utf-8 -*-
"""Celery tasks

:copyright: Copyright (c) 2015 Bivio Software, Inc.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkdebug import pkdc, pkdp

import importlib

from celery import Celery

celery = Celery('sirepo')

celery.conf.update(
    BROKER_URL='amqp://guest@localhost//',
    CELERYD_CONCURRENCY=2,
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
def start_simulation(simulation_type, workdir):
    """Call simulation's in run_background with workdir

    Args:
        simulation_type (str): currently must be warp
        workdir (py.path.local): directory
    """
    importlib.import_module('sirepo.pykern_cli.' + simulation_type).run_background(workdir)
    # Doesn't return anything
