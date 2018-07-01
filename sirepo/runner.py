# -*- coding: utf-8 -*-
u"""Run jobs

:copyright: Copyright (c) 2016 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html


decouple so can start any type of job
add is_background_import to simulation_db
select docker for that if configured and not background
need to have hard constraints on the docker container

runner.init_job() does the dispatch


"""
from __future__ import absolute_import, division, print_function
from pykern import pkcli
from pykern import pkconfig
from pykern import pkcollections
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

#: Configuration
cfg = None

# Map of jid to instance
_job_map = pkcollections.Dict()

_job_map_lock = threading.RLock()


@pkconfig.parse_none
def cfg_job_class(value):
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
    elif value is None:
        return None
    else:
        raise AssertionError('{}: unknown job_class'.format(value))


def init(app, uwsgi):
    """Initialize module"""
    if cfg.job_class is None:
        from sirepo import server
        d = 'Background'
        if server.cfg.job_queue:
            # Handle deprecated case
            d = server.cfg.job_queue
        cfg.job_class = cfg_job_class(d)
        assert not uwsgi or not issubclass(cfg.job_class, Background), \
            'uwsgi does not work if sirepo.runner.cfg.job_class=Background'


def job_is_processing(jid):
    return cfg.job_class.is_processing(jid)


def job_kill(jid):
    """Terminate job

    Args:
        jid (str): see `simulation_db.job_id`
    """
    with _job_map_lock:
        try:
            job = _job_map[jid]
        except KeyError:
            return
        lock = getattr(job, 'kill_lock', None)
        if lock:
            return
        lock = threading.RLock()
        job.kill_lock = lock
#TODO(robnagler) need a garbage collector in the event that the thread dies in
#   job.kill(). Need to terminate the job with the strongest kill signal
    with lock:
        job.kill()
    with _job_map_lock:
        try:
            job = _job_map[jid]
            if getattr(job, 'kill_lock', None) != lock:
                pkdlog('{}: job restarted by another thread', jid)
                return
            del _job_map[job.jid]
            pkdlog('{}: killed and deleted', job.jid)
        except KeyError:
            # job reaped by sigchld_handler
            pass


def job_race_condition_reap(jid):
    return cfg.job_class.race_condition_reap(jid)


def job_start(data):
    return cfg.job_class(data)


class Background(object):
    """Run as subprocess"""

    def __init__(self, data):
        with _job_map_lock:
            self.jid = simulation_db.job_id(data)
            if self.jid in _job_map:
                raise Collision(self.jid)
            self.in_kill = None
            self.cmd, self.run_dir = simulation_db.prepare_simulation(data)
            _job_map[self.jid] = self
            self.pid = None
            # This command may blow up
            self.pid = self._start_job()

    @classmethod
    def is_processing(cls, jid):
        with _job_map_lock:
            try:
                self = _job_map[jid]
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
                del _job_map[jid]
                pkdlog('{}: pid={} does not exist, removing job', jid, self.pid)
                return False
        return True

    def kill(self):
        pkdlog('{}: stopping: pid={}', self.jid, self.pid)
        sig = signal.SIGTERM
        for i in range(3):
            try:
                os.kill(self.pid, sig)
                for j in range(3):
                    time.sleep(1)
                    pid, status = os.waitpid(self.pid, os.WNOHANG)
                    if pid != 0:
                        break
                else:
                    continue
                if pid == self.pid:
                    pkdlog('{}: waitpid: status={}', pid, status)
                    break
                else:
                    pkdlog('pid={} status={}: unexpected waitpid result; job={} pid={}', pid, status, self.jid, self.pid)
                sig = signal.SIGKILL
            except OSError as e:
                if e.errno in (errno.ESRCH, errno.ECHILD):
                    # reaped by sigchld_handler()
                    return
                raise


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
            with _job_map_lock:
                if not _job_map:
                    # Can't be our job so don't waitpid.
                    # Only important at startup, when other modules
                    # are doing popens, which does a waitpid.
                    # see radiasoft/sirepo#681
                    return
                pid, status = os.waitpid(-1, os.WNOHANG)
                if pid == 0:
                    # a process that was reaped before sigchld called
                    return
                for self in _job_map.values():
                    if self.pid == pid:
                        del _job_map[self.jid]
                        pkdlog('{}: delete successful jid={}', self.pid, self.jid)
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

    def __init__(self, data):
        with _job_map_lock:
            self.jid = simulation_db.job_id(data)
            pkdc('{}: created', self.jid)
            if self.jid in _job_map:
                self = _job_map[self.jid]
                pkdlog(
                    '{}: Collision tid={} celery_state={}',
                    self.jid,
                    self.async_result,
                    self.async_result and self.async_result.state,
                )
                raise Collision(self.jid)
            self.cmd, self.run_dir = simulation_db.prepare_simulation(data)
            _job_map[self.jid] = self
            self.data = data
            _job_map[self.jid] = self
            self.async_result = self._start_job()
            pkdc(
                '{}: started tid={} dir={} queue={} len_jobs={}',
                self.jid,
                self.async_result.task_id,
                self.run_dir,
                self.celery_queue,
                len(_job_map),
            )

    @classmethod
    def is_processing(cls, jid):
        """Job is either in the queue or running"""
        with _job_map_lock:
            return bool(cls._find_job(jid))

    def kill(self):
        from celery.exceptions import TimeoutError
        res = self.async_result
        tid = res.task_id
        pkdlog('{}: killing: tid={}', self.jid, tid)
        try:
            res.revoke(terminate=True, wait=True, timeout=2, signal='SIGTERM')
        except TimeoutError as e:
            pkdlog('{}: sending a SIGKILL tid={}', self.jid, tid)
            res.revoke(terminate=True, signal='SIGKILL')


    @classmethod
    def race_condition_reap(cls, jid):
        """Race condition due to lack of mutex and reliable results.
        """
        with _job_map_lock:
            self = cls._find_job(jid)
            if self:
                res = self.async_result
                pkdlog(
                    '{}: aborting and deleting job; tid={} celery_state={}',
                    jid,
                    res,
                    res and res.state,
                )
                del _job_map[self.jid]
                res.revoke(terminate=True, signal='SIGKILL')
            else:
                pkdlog('{}: job finished finally', jid)

    @classmethod
    def _find_job(cls, jid):
        try:
            self = _job_map[jid]
        except KeyError:
            pkdlog('{}: job not found; len_jobs={}', jid, len(_job_map))
            return None
        res = self.async_result
        pkdc(
            '{}: job tid={} celery_state={} len_jobs={}',
            jid,
            res,
            res and res.state,
            len(_job_map),
        )
        if not res or res.ready():
            del _job_map[jid]
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


def _assert_celery():
    """Verify celery & rabbit are running"""
    from sirepo import celery_tasks
    import time

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
           return

    #TODO(robnagler) really should be pkconfig.Error() or something else
    # but this prints a nice message. Don't call sys.exit, not nice
    pkcli.command_error(err)


cfg = pkconfig.init(
    # default is set in init()
    job_class=(None, cfg_job_class, 'how to run jobs: Celery or Background'),
)
