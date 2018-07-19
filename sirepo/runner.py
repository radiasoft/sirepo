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
from pykern import pkcollections
from pykern import pkconfig
from pykern import pkio
from pykern import pkjinja
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp
from sirepo import simulation_db
from sirepo.template import template_common
import aenum
import errno
import os
import pwd
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

_parallel_cores = None

class State(aenum.UniqueEnum):
    INIT = 1
    START = 2
    KILL = 3
    RUN = 4
    STOP = 5

# how long to wait before assuming thread that created
# job is dead.
_INIT_TOO_LONG_SECS = 5

# time expected between created and running
_DOCKER_CREATED_TOO_LONG_SECS = _INIT_TOO_LONG_SECS

# how long to wait after first kill (TERM) to second kill (KILL)
_KILL_TIMEOUT_SECS = 3

# prefix all report names
_DOCKER_CONTAINER_PREFIX = 'srjob-'

# default is unlimited so put some real constraint
_MAX_OPEN_FILES = 1024

_DOCKER_RUN_PREFIX = (
    'run',
    '--log-driver=json-file',
    # never should be large, just for output of the monitor
    '--log-opt=max-size=1m',
    '--rm',
    '--ulimit=core=0',
    '--ulimit=nofile={}'.format(_MAX_OPEN_FILES),
)

# where docker tls files reside relative to sirepo_db_dir
_DOCKER_TLS_SUBDIR = 'runner/docker_tls'

# absolute path to _DOCKER_TLS_SUBDIR
_docker_tls_d = None

# map of docker hosts to specification and status
_docker_hosts = None

@pkconfig.parse_none
def cfg_job_class(value):
    """Return job queue class based on name

    Args:
        value (object): May be class or str.

    Returns:
        object: `Background` or `Celery` class.

    """
    if isinstance(value, type) and issubclass(value, (Background, Celery, Docker)):
        # Already initialized but may call initializer with original object
        return value
    if value == 'Celery':
        if pkconfig.channel_in('dev'):
            _assert_celery()
        return Celery
    elif value == 'Docker':
        return Docker
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
    if isinstance(cfg.job_class, Docker):
        _docker_init(app);


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
                if time.time() < self.state_changed + _INIT_TOO_LONG_SECS:
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
        for sig in (signal.SIGTERM, signal.SIGKILL):
            try:
                pkdlog('{}: kill {} pid={}', self.jid, sig, self.pid)
                os.kill(self.pid, sig)
                for j in range(_KILL_TIMEOUT_SECS):
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
                maxfd = _MAX_OPEN_FILES
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
            res.revoke(terminate=True, wait=True, timeout=_KILL_TIMEOUT_SECS, signal='SIGTERM')
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


class Docker(Base):
    """Run a code in docker"""

    def _is_processing(self):
        """Inspect container to see if still in running state"""
        out = self.__docker(['inspect', '--format={{.State.Status}}', self.cid])
        if not out:
            self.cid = None
            return False
        if out == 'running':
            return True
        if out == 'created':
            return time.time() < self.state_changed + _DOCKER_CREATED_TOO_LONG_SECS
        return False

    def _kill(self):
        if self.cid:
            pkdlog('{}: stop cid={}', self.jid, self.cid)
            self.__docker(['stop', '--time={}'.format(_KILL_TIMEOUT_SECS), self.cid])
            self.cid = None

    def _start(self):
        """Detach a process from the controlling terminal and run it in the
        background as a daemon.
        """
        #POSIT: jid is valid docker name (word chars and dash)
        self.cname = _DOCKER_CONTAINER_PREFIX + self.jid
        ctx = pkcollections.Dict(
            kill_secs=_KILL_TIMEOUT_SECS,
            run_dir=self.run_dir,
            run_log=self.run_dir.join(template_common.RUN_LOG),
            run_secs=self.__run_secs(),
            sh_cmd=self.__sh_cmd(),
        )
#TODO(robnagler) queue?
        self.docker_host = _docker_host_select(self),
        script = str(self.run_dir.join(_DOCKER_CONTAINER_PREFIX + 'run.sh'))
        with open(str(script), 'wb') as f:
            f.write(pkjinja.render_resource('runner/docker.sh', ctx))
        cmd = _DOCKER_RUN_PREFIX + (
#TODO(robnagler) configurable
            '--cpus=' + self.__cores(),
            '--detach',
            '--init',
            '--memory={}g'.format(self.__gigabytes()),
            '--name=' + self.cname,
            '--network=none',
#TODO(robnagler) this doesn't do anything
#            '--ulimit=cpu=1',
            # do not use a user name, because that may not map inside the
            # container properly. /etc/passwd on the host and guest are
            # different.
            '--user={}'.format(os.getuid()),
        ) + self.__volumes() + (
#TODO(robnagler) make this configurable per code (would be structured)
            _docker_image(),
            'bash',
            script,
        )
        self.cid = _docker_cmd(self.docker_host, cmd)
        pkdc(
            '{}: started cname={} cid={} dir={} len_jobs={} cmd={}',
            self.jid,
            self.cname,
            self.cid,
            self.run_dir,
            len(_job_map),
            cmd,
        )

    def __cores(self):
#TODO(robnagler) compute cores by interrogating each docker host
        if simulation_db.is_parallel(self.data):
            return 2
        return 1

    def __gigabytes(self):
#TODO(robnagler) compute gigabytes by interrogating host and dividing by number of processes
        if simulation_db.is_parallel(self.data):
            return 16
#TODO(robnagler) sequential processes probably don't need much memory, but maybe 2g
#TODO(robnagler) imports definitely don't need more than 1g
        return 1

    def __run_secs(self):
        if self.data['report'] == 'backgroundImport':
            return cfg.import_secs
        if simulation_db.is_parallel(self.data):
            return cfg.parallel_secs
        return cfg.sequential_secs

    def __sh_cmd(self):
        """Convert ``self.cmd`` into a bash cmd"""
        res = []
        for c in self.cmd:
            assert not "'" in c, \
                '{}: sh_cmd contains a single quote'.format(cmd)
            res.append("'{}'".format(c))
        return ' '.join(res)

    def __volumes(self):
        res = []

        def _res(src, tgt):
            res.append('--volume={}:{}'.format(src, tgt))

        if pkconfig.channel_in('dev'):
            for v in '~/src', '~/.pyenv':
                v = pkio.py_path('~/src')
                # pyenv and src shouldn't be writable, only rundir
                _res(v, v + ':ro')
        _res(self.run_dir, self.run_dir)
        return tuple(res)


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


def _docker_cmd(host, cmd):
    cmd = _docker_hosts[host].cmd_prefix + cmd
    try:
        pkdc('Running: {}', cmd)
        return subprocess.check_output(
            cmd,
            stdin=open(os.devnull),
            stderr=subprocess.STDOUT,
        ).rstrip()
    except subprocess.CalledProcessError as e:
        pkdlog('{}: failed: exit={} output={}', cmd, e.returncode, e.output)
        return None

def _docker_cmd_prefix(host, tls_d):
    return (
        'docker',
        # docker TLS port is hardwired to default
        '--host=tcp://{}:2376'.format(host),
        '--tlscacert={}'.format(tls_d.join('ca.pem')),
        '--tlscert={}'.format(tls_d.join('cert.pem')),
        '--tlskey={}'.format(tls_d.join('key.pem')),
        '--tlsverify',
    )


def _docker_host_select(docker):
    return _docker_hosts.keys()[0]

#TODO(robnagler) probably should push this to pykern also in rsconf
def _docker_image(self):
    res = cfg.docker_image
    if ':' in res:
        return res
    return res + ':' + pkconfig.cfg.channel


def _docker_init(app):
    if _docker_tls_d:
        return
    import sirepo.mpi
    _docker_tls_d = app.sirepo_db_dir.join(_DOCKER_TLS_SUBDIR)
    assert _docker_tls_d.check(dir=True), \
        '{}: tls directory does not exist'.format(_docker_tls_d)
    # Require at least three levels to the domain name
    _docker_hosts = pkcollections.Dict()
    _parallel_cores = sirepo.mpi.cfg.cores
    for d in pkio.sorted_glob(_docker_tls_d.join('*.*.*')):
        h = d.basename
        _docker_hosts[h] = pkcollections.Dict(
            name=h,
            cmd_prefix=_docker_cmd_prefix(h, d)
        )
        _docker_init_host(h)


def _docker_init_host(host):
    h = _docker_hosts[host]
#TODO(robnagler) cat /proc/cpuinfo /proc/meminfo and parse accounting for hyperthreading
# grep -m 1 "cpu cores" /proc/cpu
# cpu cores   : 8
# grep -c "physical id" /proc/cpu | uniq | wc
# physical id   : 3
    h.update(
        cores=4,
        gigabytes=8,
        parallel_jobs=[None],
        sequential_jobs=[None],
    )
    return
    j = h.cores / _parallel_cores
    assert j <= 0, \
        '{}: parallel jobs <= 0: host={} cores={} mpi.cores={}'.format(
            j,
            host,
            h.cores,
            _parallel_cores,
        )
    h.parallel_jobs = [None] * j


def _docker_run_root(host, cmd):
    return _docker_cmd(
        host,
        _DOCKER_RUN_PREFIX + (
            # allows us to interrogate the network
            '--network=host',
            # Ensure we are running as UID 0 (root). See
            # comment about about /etc/passwd
            '--user=0',
        ) + cmd,
    )


cfg = pkconfig.init(
    docker_image=('radiasoft/sirepo', str, 'docker image to run all jobs'),
    import_secs=(10, int, 'maximum runtime of backgroundImport'),
    # default is set in init(), because of server.cfg.job_gueue
    job_class=(None, cfg_job_class, 'how to run jobs: Celery or Background'),
    parallel_secs=(3600, int, 'maximum runtime of serial job'),
    sequential_secs=(300, int, 'maximum runtime of serial job'),
)

"""
persist queue
user queue

import time
import threading
from Queue import Queue

def getter(q):
    while True:
        print 'getting...'
        print q.get(), 'gotten'

def putter(q):
    for i in range(10):
        time.sleep(0.5)
        q.put(i)
        time.sleep(0.5)

q = Queue()
get_thread = threading.Thread(target=getter, args=(q,))
get_thread.daemon = True


get_thread.start()

Queue.get([block[, timeout]])


putter(q)
"""
