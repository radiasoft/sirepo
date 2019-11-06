# -*- coding: utf-8 -*-
"""TODO(e-carlin): Doc

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkconfig, pkio
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdlog, pkdexc, pkdc
from sirepo import job
from sirepo import job_driver
from sirepo import mpi
import os
import re
import socket
import subprocess
import tornado.ioloop

cfg = None

#: prefix all container names. Full format looks like: srj-p-uid
_CNAME_PREFIX = 'srj'

#: separator for container names
_CNAME_SEP = '-'

#: parse cotnainer names. POSIT: matches _cname_join()
_CNAME_RE = re.compile(_CNAME_SEP.join(('^' + _CNAME_PREFIX, r'([a-z]+)', '(.+)')))

#: map of docker host names to their machine/run specs and status
_hosts = None

# default is unlimited so put some real constraint
# TODO(e-carlin): max open files for local or nersc?
_MAX_OPEN_FILES = 1024

#: Copy of sirepo.mpi.cfg.cores to avoid init inconsistencies; only used during init_class()
_parallel_cores = None

_RUN_PREFIX = (
    'run',
    '--log-driver=json-file',
    # should never be large, just for output of the monitor
    '--log-opt=max-size=1m',
    '--rm',
    '--ulimit=core=0',
    '--ulimit=nofile={}'.format(_MAX_OPEN_FILES),
)

class DockerDriver(job_driver.DriverBase):

    instances = PKDict()

    slots = PKDict()

    def __init__(self, req, space):
        super().__init__(req, space)
        self.update(
            _cname=_cname_join(self._kind, self.uid),
            _agent_dir=req.content.userDir,
            _image = _image(),
            _host='localhost.localdomain', # TODO(e-carlin): use hosts like runner/docker.py
        )
        self.instances[self._kind].append(self)
        tornado.ioloop.IOLoop.current().spawn_callback(self._agent_start)

    def kill(self):
        if '_cid' not in self:
            return
        self._kill()

    async def _agent_start(self):
        cmd = _RUN_PREFIX + (
            # '--cpus={}'.format(slot.cores), # TODO(e-carlin): impl
            '--detach',
            '--env=SIREPO_PKCLI_JOB_AGENT_AGENT_ID={}'.format(self._agentId),
            '--env=SIREPO_PKCLI_JOB_AGENT_SUPERVISOR_URI={}'.format(self._supervisor_uri),
            # '--env=SIREPO_MPI_CORES={}'.format(slot.cores), # TODO(e-carlin): impl
            '--init',
            # '--memory={}g'.format(slot.gigabytes), # TODO(e-carlin): impl
            '--name={}'.format(self._cname), # TODO(e-carlin): impl
            '--network=host', # TODO(e-carlin): Was 'none'. I think we can use 'bridge' or 'host'
                # do not use a user name, because that may not map inside the
                # container properly. /etc/passwd on the host and guest are
                # different.
                '--user={}'.format(os.getuid()),
            ) + self._volumes() + (
                self._image,
                'bash',
                '-l',
                '-c',
                'pyenv shell py3 && sirepo job_agent',
            )
        self._cid = _cmd(self._host, cmd)

    def _kill(self):
        pkdlog('{}: stop cid={}', self.uid, self._cid)
        _cmd(
            self._host,
            ('stop', '--time={}'.format(job_driver.KILL_TIMEOUT_SECS), self._cid),
        )
        self._cid = None

    def _volumes(self):
        res = []
        def _res(src, tgt):
            res.append('--volume={}:{}'.format(src, tgt))

        if pkconfig.channel_in('dev'):
            for v in '~/src', '~/.pyenv', '~/.local':
                v = pkio.py_path(v)
                # pyenv and src shouldn't be writable, only rundir
                _res(v, v + ':ro')
        _res(self._agent_dir, self._agent_dir)
        return tuple(res)


def init_class(*args, **kwargs):
    global cfg, _hosts, _parallel_cores

    if _hosts:
        return

    cfg = pkconfig.init(
        hosts=(None, _cfg_hosts, 'execution hosts'),
        image=('radiasoft/sirepo', str, 'docker image to run all jobs'),
        parallel_slots=(1, int, 'max parallel slots'),
        sequential_slots=(1, int, 'max sequential slots'),
        tls_dir=(None, _cfg_tls_dir, 'directory containing host certs'),
    )
    if not cfg.tls_dir or not cfg.hosts:
        _init_dev_hosts()
    _hosts = PKDict()
    _parallel_cores = mpi.cfg.cores
    # Require at least three levels to the domain name
    # just to make the directory parsing easier.
    for h in cfg.hosts:
        d = cfg.tls_dir.join(h)
        _hosts[h] = PKDict(
            name=h,
            cmd_prefix=_cmd_prefix(h, d)
        )
        _init_host(h)
    assert len(_hosts) > 0, \
        '{}: no docker hosts found in directory'.format(cfg.tls_d)

    return DockerDriver.init_class(cfg)


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
        ).decode("utf-8").rstrip()
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


def _cname_join(kind, uid):
    """Create a cname or cname_prefix from kind and uid

    POSIT: matches _CNAME_RE
    """
    return _CNAME_SEP.join([_CNAME_PREFIX, kind[0], uid])


#TODO(robnagler) probably should push this to pykern also in rsconf
def _image():
    res = cfg.image
    if ':' in res:
        return res
    return res + ':' + pkconfig.cfg.channel


def _init_dev_hosts():
    from sirepo import srdb
    assert not (cfg.tls_dir or cfg.hosts), \
        'neither cfg.tls_dir and cfg.hosts nor must be set to get auto-config'
    # dev mode only; see _cfg_tls_dir and _cfg_hosts
    cfg.tls_dir = srdb.root().join('docker_tls')
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
    h.num_slots = PKDict()
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
    pats = PKDict()
    matches = PKDict()
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
