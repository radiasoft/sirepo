# -*- coding: utf-8 -*-
u"""Run jobs

:copyright: Copyright (c) 2016 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkcli
from pykern import pkconfig
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp
from sirepo import simulation_db
from sirepo.template import template_common
import errno
import os
import signal
import sys
import threading
import time
import uuid


class Background(object):
    """Run as subprocess"""

    # Map of jid to instance
    _job = {}

    # mutex for _job
    _lock = threading.RLock()

    def __init__(self, data):
        with self._lock:
            self.jid = simulation_db.job_id(data)
            if self.jid in self._job:
                raise Collision(self.jid)
            self.in_kill = None
            self.cmd, self.run_dir = simulation_db.prepare_simulation(data)
            self._job[self.jid] = self
            self.pid = None
            # This command may blow up
            self.pid = self._start_job()

    @classmethod
    def is_processing(cls, jid):
        with cls._lock:
            try:
                self = cls._job[jid]
            except KeyError:
                pkdc('{}: not found', jid)
                return False
            if self.in_kill:
                # Strange but true. The process is alive at this point so we
                # don't want to do anything like start a new process
                pkdc('{}: in_kill', jid)
                return True
            try:
                os.kill(self.pid, 0)
            except OSError:
                # Has to exist so no need to protect
                del self._job[jid]
                pkdlog('{}: pid={} does not exist, removing job', jid, self.pid)
                return False
        return True

    @classmethod
    def kill(cls, jid):
        self = None
        with cls._lock:
            try:
                self = cls._job[jid]
            except KeyError:
                return
            if self.in_kill:
                pkdlog('{}: kill in progress in another thread', jid)
                return
            nonce = uuid.uuid4()
            self.in_kill = nonce

        pkdlog('{}: stopping: pid={}', self.jid, self.pid)
        sig = signal.SIGTERM
        for i in range(3):
            try:
                os.kill(self.pid, sig)
                time.sleep(1)
                pid, status = os.waitpid(self.pid, os.WNOHANG)
                if pid == self.pid:
                    pkdlog('{}: waitpid: status={}', pid, status)
                    break
                else:
                    pkdlog('{}: unexpected waitpid result; job={} pid={}', pid, self.jid, self.pid)
                sig = signal.SIGKILL
            except OSError:
                pkdlog('{}: already reaped; job={}', self.pid, self.jid)
                return
        with cls._lock:
            try:
                self = cls._job[jid]
                if self.in_kill and self.in_kill == nonce:
                    self.in_kill = None
                    del self._job[self.jid]
                    pkdlog('{}: delete successful; pid=', self.jid, self.pid)
                    return
                pkdlog('{}: job restarted by another thread', jid)
            except KeyError:
                pkdlog('{}: job reaped by another thread', jid)

    @classmethod
    def race_condition_reap(cls, jid):
        """Job terminated, but not still in queue.

        This can happen due to race condition in is_processing. Call
        again to remove the job from the queue.
        """
        pkdlog('{}: sigchld_handler in another thread', jid)
        cls.is_processing(jid)

    @classmethod
    def sigchld_handler(cls, signum=None, frame=None):
        try:
            with cls._lock:
                if not cls._job:
                    # Can't be our job so don't waitpid.
                    # Only important at startup, when other modules
                    # are doing popens, which does a waitpid.
                    # see radiasoft/sirepo#681
                    return
                pid, status = os.waitpid(-1, os.WNOHANG)
                pkdlog('{}: waitpid: status={}', pid, status)
                for self in cls._job.values():
                    if self.pid == pid:
                        del self._job[self.jid]
                        pkdlog('{}: delete successful', self.jid)
                        return
        except OSError as e:
            if e.errno != errno.ECHILD:
                pkdlog('waitpid: OSError: {} errno={}', e.strerror, e.errno)
                # Fall through. Not much to do here

    def _start_job(self):
        """Detach a process from the controlling terminal and run it in the
        background as a daemon.

        We don't use pksubprocess. This method is not called from the MainThread
        so can't set signals.
        """
        try:
            pid = os.fork()
        except OSError as e:
            pkdlog('{}: fork OSError: {} errno={}', self.jid, e.strerror, e.errno)
            reraise
        if pid != 0:
            pkdlog('{}: started: pid={} cmd={}', self.jid, pid, self.cmd)
            return pid
        try:
            os.chdir(str(self.run_dir))
            #Don't os.setsid() so signals propagate properly
            import resource
            maxfd = resource.getrlimit(resource.RLIMIT_NOFILE)[1]
            if (maxfd == resource.RLIM_INFINITY):
                maxfd = 1024
            for fd in range(0, maxfd):
                try:
                    os.close(fd)
                except OSError:
                    pass
            sys.stdin = open(template_common.RUN_LOG, 'a+')
            assert sys.stdin.fileno() == 0
            os.dup2(0, 1)
            sys.stdout = os.fdopen(1, 'a+')
            os.dup2(0, 2)
            sys.stderr = os.fdopen(2, 'a+')
            pkdlog('{}: child will exec: {}', self.jid, self.cmd)
            sys.stderr.flush()
            try:
                simulation_db.write_status('running', self.run_dir)
                os.execvp(self.cmd[0], self.cmd)
            finally:
                pkdlog('{}: execvp error: {} errno={}', self.jid, e.strerror, e.errno)
                sys.exit(1)
        except BaseException as e:
            with open(str(self.run_dir.join(template_common.RUN_LOG)), 'a') as f:
                f.write('{}: error starting simulation: {}'.format(self.jid, e))
            raise


class Celery(object):
    """Run job in Celery (prod)"""

    # Map of jid to instance
    _job = {}

    # mutex for _job
    _lock = threading.RLock()

    def __init__(self, data):
        with self._lock:
            self.jid = simulation_db.job_id(data)
            pkdc('{}: created', self.jid)
            if self.jid in self._job:
                self = self._job[self.jid]
                pkdlog(
                    '{}: Collision tid={} celery_state={}',
                    self.jid,
                    self.async_result,
                    self.async_result and self.async_result.state,
                )
                raise Collision(self.jid)
            self.cmd, self.run_dir = simulation_db.prepare_simulation(data)
            self._job[self.jid] = self
            self.data = data
            self._job[self.jid] = self
            self.async_result = self._start_job()
            pkdc(
                '{}: started tid={} dir={} queue={} len_jobs={}',
                self.jid,
                self.async_result.task_id,
                self.run_dir,
                self.celery_queue,
                len(self._job),
            )

    @classmethod
    def is_processing(cls, jid):
        """Job is either in the queue or running"""
        with cls._lock:
            return bool(cls._find_job(jid))

    @classmethod
    def kill(cls, jid):
        from celery.exceptions import TimeoutError
        with cls._lock:
            self = cls._find_job(jid)
            if not self:
                return
            res = self.async_result
            tid = res.task_id
            pkdlog('{}: killing: tid={}', jid, tid)
        try:
            res.revoke(terminate=True, wait=True, timeout=2, signal='SIGTERM')
        except TimeoutError as e:
            pkdlog('{}: sending a SIGKILL tid={}', jid, tid)
            res.revoke(terminate=True, signal='SIGKILL')
        with cls._lock:
            self = cls._find_job(jid)
            if not self:
                return
            if self.async_result.task_id == tid:
                del self._job[self.jid]
                pkdlog('{}: deleted (killed) job; tid={} celery_state={}', jid, tid, self.async_result.state)
                return
            pkdlog(
                '{}: job reaped by another thread; old_tid={}, new_tid={}',
                jid,
                tid,
                self.async_result,
            )

    @classmethod
    def race_condition_reap(cls, jid):
        """Race condition due to lack of mutex and reliable results.
        """
        with cls._lock:
            self = cls._find_job(jid)
            if self:
                res = self.async_result
                pkdlog(
                    '{}: aborting and deleting job; tid={} celery_state={}',
                    jid,
                    res,
                    res and res.state,
                )
                del self._job[self.jid]
                res.revoke(terminate=True, signal='SIGKILL')
            else:
                pkdlog('{}: job finished finally', jid)

    @classmethod
    def _find_job(cls, jid):
        try:
            self = cls._job[jid]
        except KeyError:
            pkdlog('{}: job not found; len_jobs={}', jid, len(cls._job))
            return None
        res = self.async_result
        pkdc(
            '{}: job tid={} celery_state={} len_jobs={}',
            jid,
            res,
            res and res.state,
            len(cls._job),
        )
        if not res or res.ready():
            del self._job[jid]
            pkdlog(
                '{}: deleted errant or ready job; tid={} ready={}',
                jid,
                res,
                res and res.ready(),
            )
            return None
        return self

    def _start_job(self):
        """Detach a process from the controlling terminal and run it in the
        background as a daemon.
        """
        from sirepo import celery_tasks
        self.celery_queue = simulation_db.celery_queue(self.data)
        return celery_tasks.start_simulation.apply_async(
            args=[self.cmd, str(self.run_dir)],
            queue=self.celery_queue,
        )


class Collision(Exception):
    """Avoid using a mutex"""
    pass


def cfg_job_queue(value):
    """Return job queue class based on name

    Args:
        value (object): May be class or str.

    Returns:
        object: `Background` or `Celery` class.

    """
    if isinstance(value, type) and issubclass(value, (Celery, Background)):
        # Already initialized but may call initializer with original object
        return value
    if value == 'Celery':
        if pkconfig.channel_in('dev'):
            _assert_celery()
        return Celery
    elif value == 'Background':
        signal.signal(signal.SIGCHLD, Background.sigchld_handler)
        return Background
    else:
        pkcli.command_error('{}: unknown job_queue', value)


def _assert_celery():
    """Verify celery & rabbit are running"""
    from sirepo import celery_tasks
    err = None
    try:
        if not celery_tasks.celery.control.ping():
            err = 'You need to start Celery:\nsirepo service celery'
    except Exception:
        err = 'You need to start Rabbit:\nsirepo service rabbitmq'
    if err:
        #TODO(robnagler) really should be pkconfig.Error() or something else
        # but this prints a nice message. Don't call sys.exit, not nice
        pkcli.command_error(err)
