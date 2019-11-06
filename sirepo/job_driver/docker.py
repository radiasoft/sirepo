
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
import os
import re
import subprocess
import tornado.ioloop

cfg = None

#: prefix all container names. Full format looks like: srj-p-uid-sid-report
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
            _cname=_cname_join(self._kind, self.uid)
        )
        self.run_dir = pkio.py_path(req.content.runDir)
        self.instances[self._kind].append(self)
        tornado.ioloop.IOLoop.current().spawn_callback(self._agent_start)

    @classmethod
    def init_class(cls):
        for k in job.KINDS:
            cls.slots[k] = PKDict(
                in_use=0,
                total=cfg[k + '_slots'],
            )
            cls.instances[k] = []
            job_driver.Space.init_kind(k)
        return cls

    async def _agent_start(self):
        try:
            self._image = 'radiasoft/sirepo:dev'
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
                '--user={}'.format(os.getuid()),
            ) + self._volumes() + (
                self._image,
                'bash',
                '-l',
                '-c',
                'pyenv shell py3 && sirepo job_agent',
            )
            _cmd('localhost.localdomain', cmd)
        except Exception as e:
            pkdlog('error={} stack={}', e, pkdexc())



    def _volumes(self):
        res = []
        def _res(src, tgt):
            res.append('--volume={}:{}'.format(src, tgt))

        if pkconfig.channel_in('dev'):
            for v in '~/src', '~/.pyenv':
                v = pkio.py_path(v)
                # pyenv and src shouldn't be writable, only rundir
                _res(v, v + ':ro')
        _res(self.run_dir, self.run_dir)
        return tuple(res)

def init_class(*args, **kwargs):
    global cfg, _hosts

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
    # _parallel_cores = mpi.cfg.cores
    # Require at least three levels to the domain name
    # just to make the directory parsing easier.
    for h in cfg.hosts:
        d = cfg.tls_dir.join(h)
        _hosts[h] = PKDict(
            name=h,
            cmd_prefix=_cmd_prefix(h, d)
        )
    assert len(_hosts) > 0, \
        '{}: no docker hosts found in directory'.format(cfg.tls_d)

    return DockerDriver.init_class()

def _cmd(host, cmd):
    c = _hosts[host].cmd_prefix + cmd
    try:
        pkdc('Running: {}', ' '.join(c))
        r = subprocess.check_output(
            c,
            stdin=open(os.devnull),
            stderr=subprocess.STDOUT,
        ).rstrip()
    except subprocess.CalledProcessError as e:
        if cmd[0] == 'run':
            pkdlog('{}: failed: exit={} output={}', cmd, e.returncode, e.output)
        return None

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
    a = [_CNAME_PREFIX, kind[0]]
    if uid:
        a.append(uid)
    return _CNAME_SEP.join(a)

