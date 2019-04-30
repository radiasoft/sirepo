# -*- coding: utf-8 -*-
u"""Run jobs in Docker

Locking is very tricky, because there are many long running operations. We
try to release locks when possible when talking to docker daemons, for example.

Always grab `Job.lock` then `_SlotManager.__lock`, and try to avoid holding
both locks.

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
import socket
import subprocess
import threading
import time

#: max time expected between created and running
_CREATED_TOO_LONG_SECS = runner.INIT_TOO_LONG_SECS

#: prefix all container names. Full format looks like: srd-p-uid-sid-repot
_CNAME_PREFIX = 'srj'

#: separator for container names
_CNAME_SEP = '-'

#: parse cotnainer names. POSIT: matches _cname_join()
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

#: how often does _SlotManager wake up to _poll_running_jobs
_SLOT_MANAGER_POLL_SECS = 10

#: Copy of sirepo.mpi.cfg.cores to avoid init inconsistencies; only used during init_class()
_parallel_cores = None

#: map of docker host names to their machine/run specs and status
_hosts = None

#: used for slot creation so that order is predictable across runs
_hosts_ordered = None

#: parallel and sequential threads that run the jobs
_slot_managers = pkcollections.Dict()

#: State management for parallel and sequential allocations on all hosts
_slots = pkcollections.Dict()

#: long running job kind
_PARALLEL = 'parallel'

#: short running job kind
_SEQUENTIAL = 'sequential'

#TODO(robnagler)
#   simulation status writer with error/completed or just touch in docker.sh
#   check that the file was modified in last N seconds (probably 5)
#   if not, docker ps
#TODO(robnagler)
#   need to collect the state of all the docker hosts. extracting jobs
#   from containers and filling _slots and _slot_managers.__running and
#   runner._job_map.

class DockerJob(runner.JobBase):
    """Manage jobs running in containers"""

    def __init__(self, *args, **kwargs):
        super(DockerJob, self).__init__(*args, **kwargs)
        self.__cid = None
        #POSIT: jid is valid docker name (word chars and dash)
        self.__kind = _PARALLEL if simulation_db.is_parallel(self.data) else _SEQUENTIAL
        # Must match CNAME_RE and first letter must be distinct
        self.__cname = _cname_join(self.__kind, self.jid)
        self.__host = None

    def _is_processing(self):
        """Inspect container to see if still in running state"""
        if not self.__host:
            # Still in _SlotManager.queued_jobs
            return True
        if not self.__cid:
            return False
#TODO(robnagler) this shouldn't be done every time, need to trust
#  _SlotManager to do this
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
        """Have a slot so now ask docker to run the job

        POSIT: Job locked by caller
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
            #TODO(robnagler) other environ vars required?
            '--env=SIREPO_MPI_CORES={}'.format(slot.cores),
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
        """Queue the job and wake up the _SlotManager"""
        _slot_managers[self.__kind]._enqueue_job(self)

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


def init_class(app, *args, **kwargs):
    global cfg, _hosts, _parallel_cores

    if _hosts:
        return

    cfg = pkconfig.init(
        hosts=(None, _cfg_hosts, 'execution hosts'),
        image=('radiasoft/sirepo', str, 'docker image to run all jobs'),
        tls_dir=(None, _cfg_tls_dir, 'directory containing host certs'),
    )
    if not cfg.tls_dir or not cfg.hosts:
        _init_dev_hosts(app)
    _hosts = pkcollections.Dict()
    _parallel_cores = mpi.cfg.cores
    # Require at least three levels to the domain name
    # just to make the directory parsing easier.
    for h in cfg.hosts:
        d = cfg.tls_dir.join(h)
        _hosts[h] = pkcollections.Dict(
            name=h,
            cmd_prefix=_cmd_prefix(h, d)
        )
        _init_host(h)
    assert len(_hosts) > 0, \
        '{}: no docker hosts found in directory'.format(_tls_d)
    _init_hosts_slots_balance()
    _init_slots()
    _init_parse_jobs()
    _init_slot_managers()
    return DockerJob


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
        self.__queued_jobs = []
        self.__running_slots = pkcollections.Dict()
        self.__available_slots = slots
        assert slots, \
            '{}: no available slots'.format(self.__kind)
        self.__cname_prefix = _cname_join(self.__kind)
        random.shuffle(self.__available_slots)
        self.start()

    def run(self):
        """Start jobs if slots available else check for available"""
        pkdlog(
            '{}: {} available={}',
            self.name,
            self.__kind,
            len(self.__available_slots),
        )
        while True:
            self.__event.wait(_SLOT_MANAGER_POLL_SECS)
            got_one = False
            while True:
                with self.__lock:
                    self.__event.clear()
                    if not (self.__queued_jobs and self.__available_slots):
                        if self.__queued_jobs:
                            pkdlog(
                                'waiting: queue={} available={}',
                                [x.jid for x in self.__queued_jobs],
                                [str(x) for x in self.__available_slots],
                            )
                        break
                    j = self.__queued_jobs.pop(0)
                    s = self.__available_slots.pop(0)
                    s.job = j
                    self.__running_slots[j.jid] = s
                # have to release slot lock before locking job
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
                self._poll_running_jobs()

    def _end_job(self, job):
        """Free the slot associated with the job

        POSIT: job is locked
        """
        slot = None
        with self.__lock:
            try:
                self.__queued_jobs.remove(job)
                # No slot, just done
                return
            except ValueError:
                pass
            try:
                s = self.__running_slots[job.jid]
                if s.job == job:
                    slot = s
                    s.job = None
                    del self.__running_slots[job.jid]
            except KeyError as e:
                pkdlog(
                    '{}: PROGRAM ERROR: not in running, ignoring job: {}\n{}',
                    job.jid,
                    e,
                    pkdexc(),
                )
            if slot:
                self.__available_slots.append(slot)
                self.__event.set()

    def _enqueue_job(self, job):
        """Add to queue and ping me"""
        with self.__lock:
            pkdlog(
                'queue: jid={} queue_before={}',
                job.jid,
                [x.jid for x in self.__queued_jobs],
            )
            self.__queued_jobs.append(job)
            self.__event.set()

    def _poll_running_jobs(self):
        """Validate jobs are actually running in containers on docker hosts"""
        with self.__lock:
            if len(self.__available_slots) + len(self.__running_slots) \
                != len(_slots[self.__kind]):
                # This path is probably a bug in _SlotManager, but could be a
                # lock error so just log until we see what comes up in real-time.
                pkdlog(
                    '{}: PROGRAM ERROR: running={} available={} queued_jobs={}',
                    self.__kind,
                    len(self.__running_slots),
                    len(self.__available_slots),
                    len(self.__queued_jobs),
                )
            rh = set([s.host for s in self.__running_slots.values()])
        if not rh:
            # No jobs are running so no containers to check
            return
        # Don't hold the lock while parsing, too long
        containers = _parse_ps(rh, cname_prefix=self.__cname_prefix)
        not_in_running = []
        with self.__lock:
            # containers is not correlated at this point, but if
            # we have a job that's not in containers, then it
            # might be dead or just starting. If it is dead, it'll
            # have mismatch on the cid and jid, which is checked below.
            for jid, s in self.__running_slots.items():
                if jid not in containers:
                    # POSIT: this thread starts all containers so
                    # __running_slots can only shrink, not grow from the
                    # time we took a snapshot of the running/created/exited
                    # jobs actually on the hosts.
                    not_in_running.append(s.job)
#TODO(robnagler)
#for j in not_in_running:
#            j.cid
#            we know nothing at this point
#            so only valid if cid is the same(?)

#TODO(robnagler) sanity check on _slots & _total available and running
        # docker ps -aq


@pkconfig.parse_none
def _cfg_hosts(value):
    value = pkconfig.parse_tuple(value)
    if value:
        return value
    assert pkconfig.channel_in('dev'), \
        'required config'
    return None


@pkconfig.parse_none
def _cfg_tls_dir(value):
    if not value:
        assert pkconfig.channel_in('dev'), \
            'required config'
        return None
    res = pkio.py_path(value)
    assert res.check(dir=True), \
        'directory does not exist; value={}'.format(value)
    return res


def _cmd(host, cmd):
    c = _hosts[host].cmd_prefix + cmd
    try:
        pkdc('Running: {}', ' '.join(c))
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
    args = [
        'docker',
        # docker TLS port is hardwired
        '--host=tcp://{}:2376'.format(host),
        '--tlsverify',
    ]
    # POSIT: rsconf.component.docker creates {cacert,cert,key}.pem
    for x in 'cacert', 'cert', 'key':
        f = tls_d.join(x + '.pem')
        assert f.check(), \
            'tls file does not exist for host={}: file={}'.format(host, f)
        args.append('--tls{}={}'.format(x, f))
    return tuple(args)



def _cname_join(kind, jid=None):
    """Create a cname or cname_prefix from kind and optionally jid

    POSIT: matches _CNAME_RE
    """
    a = [_CNAME_PREFIX, kind[0]]
    if jid:
        a.append(jid)
    return _CNAME_SEP.join(a)


#TODO(robnagler) probably should push this to pykern also in rsconf
def _image():
    res = cfg.image
    if ':' in res:
        return res
    return res + ':' + pkconfig.cfg.channel


def _init_dev_hosts(app):
    assert not (cfg.tls_dir or cfg.hosts), \
        'neither cfg.tls_dir and cfg.hosts nor must be set to get auto-config'
    # dev mode only; see _cfg_tls_dir and _cfg_hosts
    cfg.tls_dir = app.sirepo_db_dir.join('docker_tls')
    cfg.hosts = ('localhost.localdomain',)
    d = cfg.tls_dir.join(cfg.hosts[0])
    if d.check(dir=True):
        return
    pkdlog('initializing docker dev env; initial docker pull will take a few minutes...')
    d.ensure(dir=True)
    for f in 'key.pem', 'cert.pem':
        o = subprocess.check_output(['sudo', 'cat', '/etc/docker/tls/' + f])
        assert o.startswith('-----BEGIN'), \
            'incorrect tls file={} content={}'.format(f, o)
        d.join(f).write(o)
    # we just reuse the same cert as the docker server since it's local host
    d.join('cacert.pem').write(o)


def _init_host(host):
    """Calculate basic machine characteristics (specs) for a host"""
    h = _hosts[host]
    _init_host_spec(h)
    _init_host_num_slots(h)


def _init_host_num_slots(h):
    """Compute how many slots available based on a fixed `_parallel_cores`"""
    h.num_slots = pkcollections.Dict()
    j = h.cores // _parallel_cores
    assert j > 0, \
        '{}: host cannot run parallel jobs, min cores required={} and cores={}'.format(
            h.name,
            _parallel_cores,
            h.cores,
        )
    h.num_slots.parallel = j
    h.num_slots.sequential = h.cores - j * _parallel_cores
    pkdc(
        '{} {} {} {}gb {}c',
        h.name,
        h.num_slots.parallel,
        h.num_slots.sequential,
        h.gigabytes,
        h.cores,
    )


def _init_host_spec(h):
    """Extract mem, cpus, and cores from /proc"""
    h.remote_ip = socket.gethostbyname(h.name)
    h.local_ip = _local_ip(h.remote_ip)
    # NOTE: this will pull the container the first time
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
    """Balance sequential and parallel slot counts"""
    global _hosts_ordered

    def _host_cmp(a, b):
        """This (local) host will get (first) sequential slots.

        Sequential slots are "faster" and don't go over NFS (usually)
        so the interactive jobs will be more responsive (hopefully).

        We don't assign sequential slots randomly, but in fixed order.
        This helps reproduce bugs, because you know the first host
        is the sequential host. Slots are then randomized
        for execution.
        """
        if a.remote_ip == a.local_ip:
            return -1
        if b.remote_ip == b.local_ip:
            return +1
        return cmp(a.name, b.name)

    def _ratio_not_ok():
        """Minimum sequential job slots should be 40% of total"""
        mp = 0
        ms = 0
        for h in _hosts.values():
            mp += h.num_slots.parallel
            ms += h.num_slots.sequential
        if mp + ms == 1:
            # Edge case where ratio calculation can't work (only dev)
            h = _hosts.values()[0]
            h.num_slots.sequential = 1
            h.num_slots.parallel = 1
            return False
        # Must be at least one parallel slot
        if mp <= 1:
            return False
#TODO(robnagler) needs to be more complex, because could have many more
# parallel nodes than sequential, which doesn't need to be so large. This
# is a good guess for reasonable configurations.
        r = float(ms) / (float(mp) + float(ms))
        return r < 0.4

    _hosts_ordered = sorted(_hosts.values(), cmp=_host_cmp)
    while _ratio_not_ok():
        for h in _hosts_ordered:
            # Balancing consists of making the first host have
            # all the sequential jobs, then the next host. This
            # is a guess at the best way to distribute sequential
            # vs parallel jobs.
            if h.num_slots.parallel > 0:
                # convert a parallel slot on first available host
                h.num_slots.sequential += _parallel_cores
                h.num_slots.parallel -= 1
                break
        else:
            raise AssertionError(
                'should never get here: {}'.format(pkdpretty(hosts)),
            )
    for h in _hosts_ordered:
        pkdlog(
            '{}: parallel={} sequential={}',
            h.name,
            h.num_slots.parallel,
            h.num_slots.sequential,
        )


def _init_parse_jobs():
    """Kill any jobs that might be running at init
    """
#TODO(robnagler) parse the jobs and re-insert into jobs and slots.
    hosts = [h.name for h in _hosts_ordered]
    containers = _parse_ps(hosts, _CNAME_PREFIX)
    for c in containers.values():
        try:
            pkdlog('{jid}@{host}: stopping container', **c)
            o = _cmd(c.host, ('rm', '--force', c.cid))
        except Exception as e:
            # Can't do anything except log and try to recover at next poll
            pkdlog(
                '{}: unexpected docker rm output: {}\n{}',
                c.host,
                e,
                pkdexc(),
            )


def _init_slots():
    """Create Slot objects based on specification per machine"""
    _slots.parallel = []
    _slots.sequential = []
    for k, s in _slots.items():
        c = _parallel_cores if k == _PARALLEL else 1
        for h in _hosts_ordered:
            ns = h.num_slots[k]
            if ns <= 0:
                continue
            g = 1
            if k == _PARALLEL:
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
    """Create SlotManager objects, which starts threads"""
    for k, s in _slots.items():
        _slot_managers[k] = _SlotManager(k, s)


def _local_ip(remote_ip):
    """Determine local IPv4 for talking to hosts

    Assumes all hosts on the same network. If this host
    is talking to hosts on two different networks, sort
    order will not put this host last in _host_cmp().

    Args:
        some_ip (str): any ip address
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect((remote_ip, 80))
    return s.getsockname()[0]


def _parse_ps(hosts, cname_prefix):
    """Parse hosts for running containers that match jobs"""
    res = pkcollections.Dict()
    for h in hosts:
        try:
            o = _cmd(
                h,
                (
                    'ps',
                    '--no-trunc',
                    '--filter',
                    'name=' + cname_prefix,
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
            # Can't do anything except log and try to recover at next poll
            pkdlog(
                '{}: PROGRAM ERROR: unexpected docker ps: {}\n{}',
                h,
                e,
                pkdexc(),
            )
    return res


def _run_root(host, cmd):
    """Run cfg.image as root to see all mem and cpus.

    This also validates the docker tls configuration at startup.
    """
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
