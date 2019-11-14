# -*- coding: utf-8 -*-
"""TODO(e-carlin): Doc

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkconfig, pkio
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdlog, pkdexc, pkdc, pkdpretty
from sirepo import job
from sirepo import job_driver
from sirepo import mpi
import functools
import itertools
import operator
import os
import re
import socket
import subprocess
import tornado.ioloop
import tornado.process

cfg = None

#: prefix all container names. Full format looks like: srj-p-uid
_CNAME_PREFIX = 'srj'

#: separator for container names
_CNAME_SEP = '-'

#: parse cotnainer names. POSIT: matches _cname_join()
_CNAME_RE = re.compile(_CNAME_SEP.join(('^' + _CNAME_PREFIX, r'([a-z]+)', '(.+)')))

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

    hosts = PKDict()

    def __init__(self, req, host):
        super().__init__(req)
        self.update(
            _cname=_cname_join(self.kind, self.uid),
            _agent_dir=req.content.userDir,
            _image = _image(),
            host=host,
        )
        self.host.drivers[self.kind].append(self)
        self.instances[self.kind].append(self)
        tornado.ioloop.IOLoop.current().spawn_callback(self._agent_start)


    @classmethod
    async def get_instance(cls, req):
        for d in list(itertools.chain(*cls.instances.values())):
            if d.uid == req.content.uid:
                if d.kind == req.kind:
                    return d
                # jobs of different kinds for the same user need to go to the
                # same host. Ex. sequential analysis jobs for parallel compute
                # jobs need to go to the same host to avoid NFS caching problems
                return cls(req, d.host)
        h = min(cls.hosts.values(), key=lambda h:len(h.drivers[req.kind]))
        return cls(req, h)

    @classmethod
    def free_slots(cls, driver):
        for d in driver.host.drivers[driver.kind]:
            if d.has_slot and not d.ops_pending_done:
                d.slot_free()

    # TODO(e-carlin): very similar code between this and local
    @classmethod
    def run_scheduler(cls, driver):
        cls.free_slots(driver)
        h = driver.host
        try:
            i = h.drivers[driver.kind].index(driver)
        except ValueError:
            # In the _websocket_free() code we remove driver from list of
            # instances.
            i = 0
        # start iteration from index of current driver to enable fair scheduling
        for d in h.drivers[driver.kind][i:] + h.drivers[driver.kind][:i]:
            ops_with_send_alloc = d.get_ops_with_send_allocation()
            if not ops_with_send_alloc:
                continue
            if ((not d.has_slot and
                 h.slots[driver.kind].in_use >= h.slots[driver.kind].total
                 )
                    or not d.websocket
                ):
                continue
            if not d.has_slot:
                assert h.slots[driver.kind].in_use < h.slots[driver.kind].total
                d.has_slot = True
                h.slots[driver.kind].in_use += 1
            for o in ops_with_send_alloc:
                assert o.opId not in d.ops_pending_done
                d.ops_pending_send.remove(o)
                d.ops_pending_done[o.opId] = o
                o.send_ready.set()

    def kill(self):
        if '_cid' not in self:
            return
        # TODO(e-carlin): Kill should set an event so caller can wait on event
        # so we know when the kill actually happens.
        tornado.ioloop.IOLoop.current().add_callback(self._kill)


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
            '--network=host', # TODO(e-carlin): Understand 'bridge' vs 'host'
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
        self._cid = await _cmd(self.host, cmd)

    async def _kill(self):
        pkdlog('{}: stop cid={}', self.uid, self._cid)
        # TODO(e-carlin): _cmd start a subprocess. Need to handle that subprocess
        # not exiting cleanly
        await _cmd(
            self.host,
            ('stop', '--time={}'.format(job_driver.KILL_TIMEOUT_SECS), self._cid),
        )
        self._cid = None

    def slot_free(self):
        self.host.slots[self.kind].in_use -= 1
        self.has_slot = False

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

    def _websocket_free(self):
        self.host.drivers[self.kind].remove(self)
        super()._websocket_free()


def init_class():
    global cfg, _parallel_cores

    _parallel_cores = mpi.cfg.cores

    cfg = pkconfig.init(
        hosts=(None, _cfg_hosts, 'execution hosts'),
        image=('radiasoft/sirepo', str, 'docker image to run all jobs'),
        parallel_slots=(1, int, 'max parallel slots'),
        sequential_slots=(1, int, 'max sequential slots'),
        tls_dir=(None, _cfg_tls_dir, 'directory containing host certs'),
    )
    if not cfg.tls_dir or not cfg.hosts:
        _init_dev_hosts()
    _init_hosts()
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


async def _cmd(host, cmd):
    c = DockerDriver.hosts[host.name].cmd_prefix + cmd
    pkdc('Running: {}', ' '.join(c))
    p = tornado.process.Subprocess(
        c,
        stdin=open(os.devnull),
        stdout=tornado.process.Subprocess.STREAM,
        stderr=subprocess.STDOUT,
    )
    r = await p.wait_for_exit()
    # TODO(e-carlin): more robust handling
    assert r == 0 , \
        '{}: failed: exit={} output={}'.format(cmd, r, p.stdout)
    return (await p.stdout.read_until_close()).decode("utf-8")

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


def _init_hosts():
    for h in cfg.hosts:
        d = cfg.tls_dir.join(h)
        DockerDriver.hosts[h] = PKDict(
            cmd_prefix=_cmd_prefix(h, d),
            drivers=PKDict(),
            name=h,
            slots=PKDict(),
        )
        for k in job.KINDS:
            DockerDriver.hosts[h].slots[k] = PKDict(
                in_use=0,
                total=cfg[k + '_slots'],
            )
            DockerDriver.hosts[h].drivers[k] = []
    assert len(DockerDriver.hosts) > 0, \
        '{}: no docker hosts found in directory'.format(cfg.tls_d)