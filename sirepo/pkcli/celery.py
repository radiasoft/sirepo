# -*- coding: utf-8 -*-
"""Wrapper to manipulate celery tasks.

:copyright: Copyright (c) 2016 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function

import inspect

from pykern.pkdebug import pkdp, pkdc
import amqp.exceptions
from celery.exceptions import TimeoutError
import celery
import json

import sirepo.celery_tasks

def kill_task(task_id):
    """Revoke the task and if that fails, terminate

    Args:
        task_id (str): task id to kill
    """
    for x in inspect.getmembers(sirepo.celery_tasks):
        if isinstance(x[1], celery.Task):
            try:
                pkdp(x[1])
                a = x[1].AsyncResult(task_id)
                # Force a check to the queue
                a.get_leaf()
                break
            except amqp.exceptions.NotFound:
                a = None
    if not a:
        print('{}: task not found'.format(task_id))
        return
    try:
        a.revoke(terminate=True, wait=True, timeout=1, signal='SIGTERM')
    except TimeoutError as e:
        a.revoke(terminate=True, signal='SIGKILL')


def list_active():
    """List the active tasks in celery queue.

    Returns:
        str: JSON dump of the tasks
    """
    # Configure celery
    import celery.task.control
    i = celery.task.control.inspect()
rabbitmqadmin get queue=myqueue requeue=true count=10


    pkdp('schedule {}', i.scheduled())
    pkdp('reserved {}', i.reserved())
    pkdp('active {}', i.active())
    return
    a = i.active()
    res = {}
    for k in a:
        if a[k]:
            res[k] = a[k]
    if not res:
        return
    return json.dumps(res, sort_keys=True, indent=2)
