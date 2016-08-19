# -*- coding: utf-8 -*-
"""Celery tasks

:copyright: Copyright (c) 2015 Bivio Software, Inc.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkconfig
pkconfig.append_load_path('sirepo')

from celery import Celery
from pykern import pkcollections
from pykern import pkio
from pykern import pksubprocess
from pykern.pkdebug import pkdc, pkdexc, pkdp
from sirepo.template import template_common

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
#TODO(robnagler) stdout/error to a log file but for dev this makes sense
    CELERY_REDIRECT_STDOUTS=False,
)

def queue_name(is_parallel):
    """Which queue to execute in

    Args:
        is_parallel (bool): is it a parallel job?

    Returns:
        str: name of queue to route task
    """
    return 'parallel' if is_parallel else 'sequential'


@celery.task
def start_simulation(cmd, run_dir):
    """Call simulation's in run_background with run_dir

    Args:
        cmd (list): simulation command line
        run_dir (py.path.local): directory
    """
    with pkio.save_chdir(run_dir):
        pksubprocess.check_call_with_signals(
            cmd,
            msg=pkdp,
            output=str(run_dir.join(template_common.RUN_LOG)),
        )
