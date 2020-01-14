# -*- coding: utf-8 -*-
"""Celery tasks

:copyright: Copyright (c) 2015 Bivio Software, Inc.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
# MUST BE FIRST
from pykern import pkconfig
pkconfig.append_load_path('sirepo')

from celery import Celery
from pykern import pkcollections
from pykern import pkio
from pykern import pksubprocess
from pykern.pkdebug import pkdc, pkdexc, pkdp, pkdlog
from sirepo.template import template_common
import py.path
import os

celery = Celery('sirepo')

cfg = pkconfig.init(
    broker_url=('amqp://guest@localhost//', str, 'Celery: queue broker url'),
    celery_result_backend=('rpc://', str, 'configure db other than default'),
    celeryd_concurrency=(1, int, 'how many worker processes to start'),
    celeryd_task_time_limit=(3600, int, 'max run time for a task in seconds'),
)

celery.conf.update(
    pkcollections.map_items(cfg, op=lambda k, v: (k.upper(), v)),
)

_SERIALIZER = 'json'

celery.conf.update(
    CELERYD_LOG_COLOR=False,
    CELERYD_MAX_TASKS_PER_CHILD=1,
    CELERYD_PREFETCH_MULTIPLIER=1,
    CELERYD_TASK_SOFT_TIME_LIMIT=celery.conf['CELERYD_TASK_TIME_LIMIT'] - 10,
    CELERY_ACCEPT_CONTENT=[_SERIALIZER],
    CELERY_ACKS_LATE=True,
    CELERY_REDIRECT_STDOUTS=not pkconfig.channel_in('dev'),
    CELERY_RESULT_PERSISTENT=True,
    CELERY_RESULT_SERIALIZER=_SERIALIZER,
    CELERY_TASK_PUBLISH_RETRY=False,
    CELERY_TASK_RESULT_EXPIRES=None,
    CELERY_TASK_SERIALIZER=_SERIALIZER,
)

# CREATE USER {user} WITH PASSWORD '{pass}';
# CREATE DATABASE {db} OWNER {user};
# export SIREPO_CELERY_TASKS_CELERY_RESULT_BACKEND='db+postgresql+psycopg2://{user}:{pass}@{host}/{db}'
#TODO(robnagler) in case this happens
#if 'postgresql' in cfg.celery_result_backend:
#    # db+postgresql+psycopg2://csruser:csrpass@localhost/celery_sirepo
#    celery.conf.update(
#        CELERY_RESULT_DB_SHORT_LIVED_SESSIONS=True,
#        # For debugging: CELERY_RESULT_ENGINE_OPTIONS={'echo': True},
#    )
#fi

#: List of queues is indexed by "is_parallel"
QUEUE_NAMES = ('sequential', 'parallel')


def queue_name(is_parallel):
    """Which queue to execute in

    Args:
        is_parallel (bool): is it a parallel job?

    Returns:
        str: name of queue to route task
    """
    return QUEUE_NAMES[int(bool(is_parallel))]


@celery.task
def start_simulation(cmd, run_dir, env):
    """Call simulation's in run_background with run_dir

    Args:
        cmd (list): simulation command line
        run_dir (str): directory
    """
    # Avoid circular import
    from sirepo import simulation_db
    run_dir = py.path.local(run_dir)
    simulation_db.hack_nfs_write_status('running', run_dir)
    e = os.environ.copy()
    e.update(env)
    with pkio.save_chdir(run_dir):
        pksubprocess.check_call_with_signals(
            cmd,
            msg=pkdlog,
            output=str(run_dir.join(template_common.RUN_LOG)),
            env=e,
        )
