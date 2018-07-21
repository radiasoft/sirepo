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
_CONTAINER_PREFIX = 'srjob-'

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

#: Copy of sirepo.mpi.cfg.cores
_parallel_cores = None

# absolute path to _TLS_SUBDIR
_tls_d = None

# map of docker hosts to specification and status
_hosts = None

# hosts.values() in alphabetical order
_hosts_ordered = None

# available slots for execution
_slots = None

_dameon = None

class Docker(runner.Base):
    """Run a code in docker"""

    def __init__(self, *args, **kwargs):
        super(Docker, self).__init__(*args, **kwargs)
        self.__cid = None
        #POSIT: jid is valid docker name (word chars and dash)
        self.__cname = _CONTAINER_PREFIX + self.jid
        self.__kind = 'parallel' if simulation_db.is_parallel(self.data) else 'sequential'
        self.__slot = None

    def _is_processing(self):
        """Inspect container to see if still in running state"""
        if not self.__cid:
            return False
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
        if self.__cid:
            pkdlog('{}: stop cid={}', self.jid, self.__cid)
            _cmd(
                self.__host,
                ('stop', '--time={}'.format(runner.KILL_TIMEOUT_SECS), self.__cid),
            )
            self.__cid = None
            slot = self.__slot
            self.__slot = None
            _slot_manager[self.__kind].free_slot(slot)

    def _slot_start(self, slot):
        """Have a slot so now start docker"""
        with self.lock:
            self.__slot = slot
            ctx = pkcollections.Dict(
                kill_secs=runner.KILL_TIMEOUT_SECS,
                run_dir=self.run_dir,
                run_log=self.run_dir.join(template_common.RUN_LOG),
                run_secs=self.run_secs(),
                sh_cmd=self.__sh_cmd(),
            )
            self.__image = _image()
            script = str(self.run_dir.join(_CONTAINER_PREFIX + 'run.sh'))
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
            pkdc(
                '{}: started cname={} cid={} dir={} cmd={}',
                self.jid,
                self.__cname,
                self.__cid,
                self.run_dir,
                cmd,
            )

    def _start(self):
        """Detach a process from the controlling terminal and run it in the
        background as a daemon.
        """
        _slot_manager[self.__kind].start_job(self)

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
    return Docker

class _Slot(pkcollections.Dict):
    pass


#TODO(robnagler) consider multiprocessing
class _SlotManager(threading.Thread):

    def __init__(self, kind, *args, **kwargs):
        super(_Daemon, self).__init__(*args, **kwargs)
        self.daemon = True
        self.__event = threading.Event()
        self.__kind = kind
        self.__lock = threading.RLock()
        self.__pending = []
        self.__running = []
        self.__available = _slots[kind]
        random.shuffle(self.__available)
        self.start()

    def free_slot(self, slot):
        # This will throw an exception (Full), which shouldn't happen
        with self.__lock:
            self.__available.append(slot)
            self.__event.set()

    def run(self):
        while True:
            if self.__event.wait(_SLOT_MANAGER_POLL_SECS):
                j = None
                with self.__lock:
                    if self.__pending and self.__available:
                        # order here matters in case of a weird exception
                        j = self.__pending.pop(0)
                        self.__running.append(j)
                        s = self.__available.pop(0)
                if j:
                    j._slot_start(s)
            else:
                with self.__lock:
                    hosts = set([j._slot for j in self.__running])
                        docker ps -aq
                        # check the container is running

    def start_job(self, job):
        # This will throw an exception (Full), which shouldn't happen
        with self.__lock():
            self.__pending.append(job)
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
    global _hosts, _parallel_cores

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
    pkdc('{name} {parallel} {sequential} {gigabytes}gb {cores}c', **h, **h.num_slots)


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
        '{}: expected a gigabyte or more'.format(matches.mem[0])
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
    global _slots

    _slots = pkcollections.Dict(
        parallel=[],
        sequential=[],
    )
    for k, s in _slots.items():
        c = _parallel_cores if k == 'parallel' else 1
        for h in _hosts_ordered:
            ns = h.num_slots[k]
            g = 1
            if k == 'parallel':
                # Leave some ram for caching and OS
                g = (h.gigabyte -  2) // ns
                if g < 1:
                    g = 1
            for i in range(ns):
                s.append(_Slot(
                    kind=k,
                    host=h.name,
                    index=i,
                    cores=c,
                    gigabytes=g,
                ))


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
