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
import aenum
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


class State(aenum.UniqueEnum):
    INIT = 1
    START = 2
    KILL = 3
    RUN = 4
    STOP = 5

# how long to wait before assuming thread that created
# job is dead.
_INIT_TOO_LONG_SECS = 5


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
        signal.signal(signal.SIGCHLD, Background._sigchld_handler)
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
    with _job_map_lock:
        try:
            job = _job_map[jid]
        except KeyError:
            return False
    return job.is_processing()


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
    job.kill()


def job_race_condition_reap(jid):
    return job_kill(jid)


def job_start(data):
    with _job_map_lock:
        jid = simulation_db.job_id(data)
        if jid in _job_map:
#TODO(robnagler) assumes external check of is_processing,
# which server._simulation_run_status does do, but this
# could be cleaner. Really want a reliable daemon thread
# to manage all this.
            raise Collision(jid)
        job = cfg.job_class(jid, data)
        _job_map[jid] = job
    job.start()


class Base(object):
    """Super of all job classes"""
    def __init__(self, jid, data):
        self.data = data
        self.jid = jid
        self.lock = threading.RLock()
        self.set_state(State.INIT)

    def is_processing(self):
        with self.lock:
            if self.state == State.RUN:
                if self._is_processing():
                    return True
            elif self.state == State.INIT:
                if time.time() < self.state_changed + INIT_TOO_LONG_SECS:
                    return True
            else:
                assert self.state in (State.START, State.KILL, State.STOP), \
                    '{}: invalid state for jid='.format(self.state, self.jid)
        # reap the process in a non-running state
        self.kill()
        return False

    def kill(self):
        with self.lock:
            if self.state in (State.RUN, State.START, State.KILL):
                # normal case (RUN) or thread died while trying to kill job
                self._kill()
            elif not self.state in (State.INIT, State.STOP):
                raise AssertionError(
                    '{}: invalid state for jid='.format(self.state, self.jid),
                )
            self.set_state(State.STOP)
        with _job_map_lock:
            try:
                if self == _job_map[self.jid]:
                    del _job_map[self.jid]
            except KeyError:
                # stopped and no longer in map
                return

    def set_state(self, state):
        self.state = state
        self.state_changed = time.time()

    def start(self):
        with self.lock:
            if self.state == State.STOP:
                # Something killed between INIT and START so don't start
                return
            elif self.state in (State.KILL, State.RUN):
                # normal case (RUN) or race condition on start/kill
                # with a thread that died while trying to kill this
                # job before it was started.  Have to finish the KILL.
                self.kill()
                return
            else:
                # race condition that doesn't seem possible
                assert self.state == State.INIT, \
                    '{}: unexpected state for jid={}'.format(self.state, self.jid)
            self.set_state(State.START)
            self.cmd, self.run_dir = simulation_db.prepare_simulation(self.data)
            self._start()
            self.set_state(State.RUN)


class Background(Base):
    """Run as subprocess"""

    def _is_processing(self):
        try:
            os.kill(self.pid, 0)
        except OSError:
            self.pid = 0
            return False
        return True

    def _kill(self):
        if self.pid == 0:
            return
        pid = self.pid
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
                    self.pid = 0
                    break
                else:
                    pkdlog(
                        'pid={} status={}: unexpected waitpid result; job={} pid={}',
                        pid,
                        status,
                        self.jid,
                        self.pid,
                    )
                sig = signal.SIGKILL
            except OSError as e:
                if not e.errno in (errno.ESRCH, errno.ECHILD):
                    raise
                # reaped by _sigchld_handler()
                return

    @classmethod
    def _sigchld_handler(cls, signum=None, frame=None):
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
                    # state of 'pid' is unknown since outside self.lock
                    if isinstance(self, Background) and getattr(self, 'pid', 0) == pid:
                        pkdlog('{}: waitpid pid={} status={}', self.jid, pid, status)
                        break
                else:
                    pkdlog('pid={} status={}: unexpected waitpid', pid, status)
                    return
            with self.lock:
                self.pid = 0
                self.kill()
        except OSError as e:
            if not e.errno in (errno,ESRCH, errno.ECHILD):
                pkdlog('waitpid: OSError: {} errno={}', e.strerror, e.errno)

    def _start(self):
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
            self.pid = pid
            return
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


class Celery(Base):
    """Run job in Celery (prod)"""

    def _is_processing(self):
        """Job is either in the queue or running"""
        res = getattr(self, 'async_result', None)
        return res and not res.ready()

    def _kill(self):
        from celery.exceptions import TimeoutError
        if not self._is_processing():
            return False
        res = self.async_result
        tid = getattr(res, 'task_id', None)
        pkdlog('{}: kill SIGTERM tid={}', self.jid, tid)
        try:
            res.revoke(terminate=True, wait=True, timeout=2, signal='SIGTERM')
        except TimeoutError as e:
            pkdlog('{}: kill SIGKILL tid={}', self.jid, tid)
            res.revoke(terminate=True, signal='SIGKILL')


    def _start(self):
        """Detach a process from the controlling terminal and run it in the
        background as a daemon.
        """
        from sirepo import celery_tasks
        self.celery_queue = simulation_db.celery_queue(self.data)
        self.async_result = celery_tasks.start_simulation.apply_async(
            args=[self.cmd, str(self.run_dir)],
            queue=self.celery_queue,
        )
        pkdc(
            '{}: started tid={} dir={} queue={} len_jobs={}',
            self.jid,
            self.async_result.task_id,
            self.run_dir,
            self.celery_queue,
            len(_job_map),
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
