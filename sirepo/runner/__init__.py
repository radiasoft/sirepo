# -*- coding: utf-8 -*-
u"""Run jobs

:copyright: Copyright (c) 2016-2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkcli
from pykern import pkcollections
from pykern import pkconfig
from pykern import pkinspect
from pykern import pkio
from pykern import pkjinja
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp, pkdpretty
from sirepo import simulation_db
from sirepo.template import template_common
import aenum
import errno
import importlib
import os
import re
import signal
import subprocess
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

_JOB_CLASSES = ('background', 'celery', 'docker', 'container')

_JOB_CLASS_DEFAULT = _JOB_CLASSES[0]

#: how long to wait before assuming thread that created job is dead.
INIT_TOO_LONG_SECS = 5

# how long to wait after first kill (TERM) to second kill (KILL)
KILL_TIMEOUT_SECS = 3

# default is unlimited so put some real constraint
MAX_OPEN_FILES = 1024

# Singleton holding which job class that was imported
_job_class = None


def init(app, use_reloader):
    """Initialize module"""
    if use_reloader and os.environ.get('WERKZEUG_RUN_MAIN') != 'true':
        # avoid first call to init() when using reloader
        return
    global _job_class

    if _job_class:
        return
    if cfg.job_class is None:
        from sirepo import server
        d = _JOB_CLASS_DEFAULT
        if server.cfg.job_queue:
            # Handle deprecated case
            d = server.cfg.job_queue.lower()
        cfg.job_class = d
    m = importlib.import_module(
        pkinspect.module_name_join((
            __name__,
            cfg.job_class,
        )),
    )
    _job_class = m.init_class(app)


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
        job = _job_class(jid, data)
        _job_map[jid] = job
    job.start()


class JobBase(object):
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

    def run_secs(self):
        if self.data['report'] == 'backgroundImport':
            return cfg.import_secs
        if simulation_db.is_parallel(self.data):
            return cfg.parallel_secs
        return cfg.sequential_secs

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

    def _error_during_start(self, exception, stack):
        """An exception happened, log what you can.

        Callback from implementations

        POSIT: job already locked or in subprocess (see Background._start)
        """
        try:
            with open(str(self.run_dir.join(template_common.RUN_LOG)), 'a') as f:
                f.write(
                    '{}: error starting simulation: {}\n{}'.format(
                        self.jid,
                        exception,
                        stack,
                    ),
                )
            simulation_db.write_status('error', self.run_dir)
            pkdlog('{}: unable to start job: {} {}', self.jid, exception, stack)
        except Exception:
            pass

    def _is_state_ok_to_start(self):
        """Is the state START or RUN?

        Callback from implementations

        POSIT: job already locked
        """
        return self.state in (State.START, State.RUN)


class Collision(Exception):
    """Avoid using a mutex"""
    pass


def _cfg_job_class(value):
    """Return job queue class based on name

    Args:
        value (object): May be class or str.

    Returns:
        object: `Background` or `Celery` class.

    """
    v = value.lower()
    assert v in _JOB_CLASSES, \
        '{}: invalid job_class, not in {}'.format(v, _JOB_CLASSES)
    return v


cfg = pkconfig.init(
    import_secs=(10, int, 'maximum runtime of backgroundImport'),
    # default is set in init(), because of server.cfg.job_gueue
    job_class=(
        None,
        _cfg_job_class,
        'how to run jobs: {}'.format(', '.join(_JOB_CLASSES)),
    ),
    parallel_secs=(3600, int, 'maximum runtime of serial job'),
    sequential_secs=(300, int, 'maximum runtime of serial job'),
)
