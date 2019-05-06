# -*- coding: utf-8 -*-
u"""Run jobs

:copyright: Copyright (c) 2016-2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkcli
from pykern import pkconfig
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp, pkdpretty
from sirepo import celery_tasks
from sirepo import runner
from sirepo import simulation_db
import time


class CeleryJob(runner.JobBase):
    """Run job in Celery (prod)"""

    def __init__(self, *args, **kwargs):
        super(CeleryJob, self).__init__(*args, **kwargs)
        self.__async_result = None

    def _is_processing(self):
        """Job is either in the queue or running"""
        res = self.__async_result
        return res and not res.ready()

    def _kill(self):
        from celery.exceptions import TimeoutError
        if not self._is_processing():
            return False
        res = self.__async_result
        tid = getattr(res, 'task_id', None)
        pkdlog('{}: kill SIGTERM tid={}', self.jid, tid)
        try:
            res.revoke(terminate=True, wait=True, timeout=runner.KILL_TIMEOUT_SECS, signal='SIGTERM')
        except TimeoutError as e:
            pkdlog('{}: kill SIGKILL tid={}', self.jid, tid)
            res.revoke(terminate=True, signal='SIGKILL')


    def _start(self):
        """Detach a process from the controlling terminal and run it in the
        background as a daemon.
        """
        self.__celery_queue = simulation_db.celery_queue(self.data)
        self.__async_result = celery_tasks.start_simulation.apply_async(
            args=[self.cmd, str(self.run_dir)],
            queue=self.__celery_queue,
        )
        pkdc(
            '{}: started tid={} dir={} queue={}',
            self.jid,
            self.__async_result.task_id,
            self.run_dir,
            self.__celery_queue,
        )


def init_class(app, *args, **kwargs):
    """Verify celery & rabbit are running"""
    if pkconfig.channel_in('dev'):
        return CeleryJob
    for x in range(10):
        err = None
        try:
            if not celery_tasks.celery.control.ping():
                err = 'You need to start Celery:\nsirepo service celery'
        except Exception:
            err = 'You need to start Rabbit:\nsirepo service rabbitmq'
            # Rabbit doesn't have a long timeout, but celery ping does
            time.sleep(.5)
        if not err:
           return CeleryJob
    #TODO(robnagler) really should be pkconfig.Error() or something else
    # but this prints a nice message. Don't call sys.exit, not nice
    pkcli.command_error(err)
