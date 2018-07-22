# -*- coding: utf-8 -*-
u"""Run jobs in Docker

:copyright: Copyright (c) 2016-2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkcollections
from pykern import pkconfig
from pykern import pkio
from pykern import pkjinja
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp, pkdpretty
from sirepo import mpi
from sirepo import runner
from sirepo import simulation_db
from sirepo.template import template_common
import os
import random
import re
import subprocess
import threading
import Queue
import time

# time expected between created and running
_CREATED_TOO_LONG_SECS = runner.INIT_TOO_LONG_SECS

# prefix all report names
_CNAME_PREFIX = 'srd'

_CNAME_SEP = '-'

# Must match cname generation in Docker.__init__
_CNAME_RE = re.compile(_CNAME_SEP.join(('^' + _CNAME_PREFIX, r'([a-z]+)', '(.+)')))

_RUN_PREFIX = (
    'run',
    '--log-driver=json-file',
    # never should be large, just for output of the monitor
    '--log-opt=max-size=1m',
    '--rm',
    '--ulimit=core=0',
    '--ulimit=nofile={}'.format(runner.MAX_OPEN_FILES),
)

# where docker tls files reside relative to sirepo_db_dir
_TLS_SUBDIR = 'runner/docker_tls'

_SLOT_MANAGER_POLL_SECS = 10

#: Copy of sirepo.mpi.cfg.cores
_parallel_cores = None

# absolute path to _TLS_SUBDIR
_tls_d = None

# map of docker hosts to specification and status
_hosts = None

# hosts.values() in alphabetical order
_hosts_ordered = None

_dameon = None

_slot_managers = pkcollections.Dict()

_slots = pkcollections.Dict()

#TODO(robnagler)
#   simulation status writer with error/completed or just touch in docker.sh
#   check that the file was modified in last N seconds (probably 5)
#   if not, docker ps

class Docker(runner.Base):
    """Run a code in docker"""

    def __init__(self, *args, **kwargs):
        super(Docker, self).__init__(*args, **kwargs)
        self.__cid = None
        #POSIT: jid is valid docker name (word chars and dash)
        self.__kind = 'parallel' if simulation_db.is_parallel(self.data) else 'sequential'
        # Must match CNAME_RE
        self.__cname = _CNAME_SEP.join((_CNAME_PREFIX, self.__kind[0:3], self.jid))
        self.__host = None

    def _is_processing(self):
        """Inspect container to see if still in running state"""
        if not self.__host:
            # Still in _SlotManager.pending_jobs
            return True
        if not self.__cid:
            return False
#TODO(robnagler) this shouldn't be done every time
        out = _cmd(
            self.__host,
            ('inspect', '--format={{.State.Status}}', self.__cid),
        )
        if not out:
            self.__cid = None
            return False
        if out == 'running':
            return True
        if out == 'created':
            return time.time() < self.state_changed + _CREATED_TOO_LONG_SECS
        return False

    def _kill(self):
        """Stop the container and free the slot if was started

        POSIT: locked by caller
        """
        if self.__cid:
            pkdlog('{}: stop cid={}', self.jid, self.__cid)
            _cmd(
                self.__host,
                ('stop', '--time={}'.format(runner.KILL_TIMEOUT_SECS), self.__cid),
            )
            self.__cid = None
        # NOTE: job is locked
        _slot_managers[self.__kind]._end_job(self)

    def _slot_start(self, slot):
        """Have a slot so now start docker

        POSIT: locked by caller
        """
        # __host is sentinel of the start attempt
        self.__host = slot.host
        ctx = pkcollections.Dict(
            kill_secs=runner.KILL_TIMEOUT_SECS,
            run_dir=self.run_dir,
            run_log=self.run_dir.join(template_common.RUN_LOG),
            run_secs=self.run_secs(),
            sh_cmd=self.__sh_cmd(),
        )
        self.__image = _image()
        script = str(self.run_dir.join('runner-docker.sh'))
        with open(str(script), 'wb') as f:
            f.write(pkjinja.render_resource('runner/docker.sh', ctx))
        cmd = _RUN_PREFIX + (
            '--cpus={}'.format(slot.cores),
            '--detach',
            '--init',
            '--memory={}g'.format(slot.gigabytes),
            '--name={}'.format(self.__cname),
            '--network=none',
#TODO(robnagler) this doesn't do anything
#            '--ulimit=cpu=1',
            # do not use a user name, because that may not map inside the
            # container properly. /etc/passwd on the host and guest are
            # different.
            '--user={}'.format(os.getuid()),
        ) + self.__volumes() + (
#TODO(robnagler) make this configurable per code (would be structured)
            self.__image,
            'bash',
            script,
        )
        self.__cid = _cmd(slot.host, cmd)
        simulation_db.write_status('running', self.run_dir)
        pkdlog(
            '{}: started slot={} cid={} dir={} cmd={}',
            self.__cname,
            slot,
            self.__cid,
            self.run_dir,
            cmd,
        )

    def _start(self):
        """Detach a process from the controlling terminal and run it in the
        background as a daemon.
        """
        _slot_managers[self.__kind]._start_job(self)

    def __sh_cmd(self):
        """Convert ``self.cmd`` into a bash cmd"""
        res = []
        for c in self.cmd:
            assert not "'" in c, \
                '{}: sh_cmd contains a single quote'.format(cmd)
            res.append("'{}'".format(c))
        return ' '.join(res)

    def __str__(self):
        return '{}({}{})'.format(
            self.__class__.__name__,
            self.jid,
            ',' + self.__cid if self.__cid else '',
        )

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


def init_class(app, uwsgi):
    global _hosts, _tls_d, _parallel_cores

    if _tls_d:
        return
    _tls_d = app.sirepo_db_dir.join(_TLS_SUBDIR)
    assert _tls_d.check(dir=True), \
        '{}: tls directory does not exist'.format(_tls_d)
    # Require at least three levels to the domain name
    _hosts = pkcollections.Dict()
    _parallel_cores = mpi.cfg.cores
    for d in pkio.sorted_glob(_tls_d.join('*.*.*')):
        h = d.basename.lower()
        _hosts[h] = pkcollections.Dict(
            name=h,
            cmd_prefix=_cmd_prefix(h, d)
        )
        _init_host(h)
    assert len(_hosts) > 0, \
        '{}: no docker hosts found in directory'.format(_tls_d)
    _init_hosts_slots_balance()
    _init_slots()
    _init_slot_managers()
    return Docker


class _Slot(pkcollections.Dict):
    def __str__(self):
        return '{}({},{},{}{})'.format(
            self.__class__.__name__,
            self.host,
            self.kind,
            self.index,
            ',' + self.job.jid if self.job else '',
        )


#TODO(robnagler) consider multiprocessing
class _SlotManager(threading.Thread):

    def __init__(self, kind, slots, *args, **kwargs):
        super(_SlotManager, self).__init__(*args, **kwargs)
        self.daemon = True
        self.__event = threading.Event()
        self.__kind = kind
        self.__lock = threading.RLock()
        self.__pending_jobs = []
        self.__running = pkcollections.Dict()
        self.__available = slots
        self.__cname_prefix = _CNAME_SEP.join((_CNAME_PREFIX, self.__kind[0:3]))
        random.shuffle(self.__available)
        self.start()

    def run(self):
        """Start jobs if slots available else check for available"""
        pkdlog('{}: {}', self.name, self.__kind)
        while True:
            self.__event.wait(_SLOT_MANAGER_POLL_SECS)
            got_one = False
            while True:
                with self.__lock:
                    self.__event.clear()
                    if not (self.__pending_jobs and self.__available):
                        # nothing to do or nothing we can do
                        break
                    j = self.__pending_jobs.pop(0)
                    s = self.__available.pop(0)
                    s.job = j
                    self.__running[j.jid] = s
                try:
                    with j.lock:
                        if j._is_state_ok_to_start():
                            j._slot_start(s)
                            got_one = True
                except Exception as e:
                    j._error_during_start(e, pkdexc())
                    try:
                        j.kill()
                    except Exception as e:
                        pkdlog(
                            '{}: error during cleanup after error: {}\n{}',
                            j.jid,
                            e,
                            pkdexc(),
                        )
            if not got_one:
                self._poll_status()

    def _end_job(self, job):
        """Free the slot associated with the job"""
        # NOTE: job is locked
        slot = None
        with self.__lock:
            try:
                self.__pending_jobs.remove(job)
                # No slot, just done
                return
            except ValueError:
                pass
            try:
                s = self.__running[job.jid]
                if s.job == job:
                    slot = s
                    s.job = None
                    del self.__running[job.jid]
            except KeyError as e:
                pkdlog(
                    '{}: PROGRAM ERROR: not in running, ignoring job: {}\n{}',
                    job.jid,
                    e,
                    pkdexc(),
                )
            if slot:
                self.__available.append(slot)
                self.__event.set()

    def _parse_ps(self, hosts):
        res = pkcollections.Dict()
        for h in hosts:
            try:
                o = _cmd(
                    h,
                    (
                        'ps',
                        '--no-trunc',
                        '--filter',
                        'name=' + self.__cname_prefix,
                        # Do not filter on running, because "created" is
                        # the same as "running" and "exited" is still running
                        # from our perspective since '--rm' is passed.
                        '--format',
                        '{{.ID}} {{.Names}}',
                    )
                )
                for l in o.splitlines():
                    i, n = l.split()
                    m = _CNAME_RE.search(n)
                    jid = m.group(2)
                    assert not jid in res, \
                        '{}: duplicate jid on ({},{}) and {}'.format(
                            jid,
                            h,
                            i,
                            res[jid],
                        )
                    res[jid] = pkcollections.Dict(host=h, cid=i, jid=jid)
            except Exception as e:
                pkdlog(
                    '{}: PROGRAM ERROR: docker ps incorrect: {}\n{}',
                    h,
                    e,
                    pkdexc(),
                )
        return res

    def _poll_status(self):
        with self.__lock:
            if len(self.__available) + len(self.__running) != len(_slots[self.__kind]):
                pkdlog(
                    '{}: COUNTS ERROR: running={} available={} pending_jobs={}',
                    self.__kind,
                    len(self.__running),
                    len(self.__available),
                    len(self.__pending_jobs),
                )
#TODO(robnagler) need to reason through this
            # List of containers known to be created, but they may not be running
            # yet.
            hosts = set([s.host for s in self.__running.values()])
        if not hosts:
            return
        jobs = self._parse_ps(hosts)
        dead = []
        with self.__lock:
            for jid, s in self.__running.items():
                if jid not in jobs:
                    # POSIT: this thread starts all containers so
                    # __running can only shrink, not grow from the
                    # time we took a snapshot of the running/created/exited
                    # jobs actually on the hosts.
                    dead.append(s.job)
        for j in dead:
            we know nothing at this point
            so only valid if cid is the same(?)
            pkdp('{}', dead)

#TODO(robnagler) sanity check on _slots & _total available and running
        # docker ps -aq

    def _start_job(self, job):
        with self.__lock:
            self.__pending_jobs.append(job)
            self.__event.set()


def _cmd(host, cmd):
    c = _hosts[host].cmd_prefix + cmd
    try:
        pkdc('Running: {}', c)
        return subprocess.check_output(
            c,
            stdin=open(os.devnull),
            stderr=subprocess.STDOUT,
        ).rstrip()
    except subprocess.CalledProcessError as e:
        if cmd[0] == 'run':
            pkdlog('{}: failed: exit={} output={}', cmd, e.returncode, e.output)
        return None

def _cmd_prefix(host, tls_d):
    return (
        'docker',
        # docker TLS port is hardwired to default
        '--host=tcp://{}:2376'.format(host),
        '--tlscacert={}'.format(tls_d.join('ca.pem')),
        '--tlscert={}'.format(tls_d.join('cert.pem')),
        '--tlskey={}'.format(tls_d.join('key.pem')),
        '--tlsverify',
    )


#TODO(robnagler) probably should push this to pykern also in rsconf
def _image():
    res = runner.cfg.docker_image
    if ':' in res:
        return res
    return res + ':' + pkconfig.cfg.channel


def _init_host(host):
    h = _hosts[host]
    _init_host_spec(h)
    _init_host_num_slots(h)


def _init_host_num_slots(h):
    h.num_slots = pkcollections.Dict()
    j = h.cores // _parallel_cores
    assert j > 0, \
        '{}: host cannot run parallel jobs, min cores required={} and cores={}'.format(
            host,
            _parallel_cores,
            h.cores,
        )
    h.num_slots.parallel = j
    # Might be 0 see _init_hosts_slots_balance
    h.num_slots.sequential = h.cores - j * _parallel_cores
    pkdc(
        '{} {} {} {gigabytes}gb {cores}c',
        h.name,
        h.num_slots.parallel,
        h.num_slots.sequential,
        h.gigabytes,
        h.cores,
    )


def _init_host_spec(h):
    out = _run_root(h.name, ('cat', '/proc/cpuinfo', '/proc/meminfo'))
    pats = pkcollections.Dict()
    matches = pkcollections.Dict()
    for k, p in (
        # MemTotal:        8167004 kB
        # physical id	: 0
        # cpu cores	: 4
        ('mem', 'MemTotal'),
        ('cpus', 'physical id'),
        ('cores', 'cpu cores'),
    ):
        pats[k] = re.compile('^' + p + r'.*\s(\d+)')
        matches[k] = []
    for l in out.splitlines():
        for k, p in pats.items():
            m = p.search(l)
            if m:
                matches[k].append(int(m.group(1)))
                break
    assert len(matches.mem) == 1, \
        '{}: expected only one match for MemTotal'.format(matches.mem)
    h.gigabytes = matches.mem[0] // 1048576
    assert h.gigabytes > 0, \
        '{}: expected a 1GB or more'.format(matches.mem[0])
    c = len(set(matches.cpus))
    assert c > 0, \
        'physical id: not found'
    assert len(set(matches.cores)) == 1, \
        '{}: expecting all "cpu cores" values to be the same'.format(matches.cores)
    h.cores = c * matches.cores[0]


def _init_hosts_slots_balance():
    global _hosts_ordered

    def _ratio_not_ok():
        mp = 0
        ms = 0
        for h in _hosts.values():
            mp += h.num_slots.parallel
            ms += h.num_slots.sequential
        r = float(ms) / (float(mp) + float(ms))
        if mp + ms == 1:
            # Edge case where ratio calculation can't work
            h = _hosts.values()[0]
            h.num_slots.sequential = 1
            h.num_slots.parallel = 1
            return False
#TODO(robnagler) needs to be more complex, because could have many more
# parallel nodes than sequential, which doesn't need to be so large. This
# is a good guess for reasonable configurations.
        return r < 0.4

    ho = sorted(_hosts.values(), key=lambda h: h.name)
    while _ratio_not_ok():
        for h in ho:
            if h.num_slots.parallel > 0:
                # convert a parallel slot on first available host
                h.num_slots.sequential += _parallel_cores
                h.num_slots.parallel -= 1
                break
        else:
            raise AssertionError(
                'should never get here: {}'.format(pkdpretty(hosts)),
            )
    # thread safe
    _hosts_ordered = ho


def _init_slots():
    _slots.parallel = []
    _slots.sequential = []
    for k, s in _slots.items():
        c = _parallel_cores if k == 'parallel' else 1
        for h in _hosts_ordered:
            ns = h.num_slots[k]
            g = 1
            if k == 'parallel':
                # Leave some ram for caching and OS
                g = (h.gigabytes -  2) // ns
                if g < 1:
                    g = 1
            for i in range(ns):
                s.append(_Slot(
                    cores=c,
                    gigabytes=g,
                    host=h.name,
                    index=i,
                    job=None,
                    kind=k,
                ))


def _init_slot_managers():
    for k, s in _slots.items():
        _slot_managers[k] = _SlotManager(k, s)


def _run_root(host, cmd):
    return _cmd(
        host,
        _RUN_PREFIX + (
            # allows us to interrogate the network
            '--network=host',
            # Ensure we are running as UID 0 (root). See
            # comment about about /etc/passwd
            '--user=0',
            _image(),
        ) + cmd,
    )
