# -*- coding: utf-8 -*-
"""TODO(e-carlin): Doc

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkconfig, pkio
from pykern.pkcollections import PKDict
import pykern.pkcollections
from pykern.pkdebug import pkdp, pkdlog, pkdexc, pkdc, pkdpretty
from sirepo import job
from sirepo import job_driver
from sirepo import mpi
import io
import itertools
import os
import re
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

class DockerDriver(job_driver.DriverBase):

    instances = PKDict()

    hosts = PKDict()

    def __init__(self, req, host):
        super().__init__(req)
        self.update(
            _cname=_cname_join(self.kind, self.uid),
            _image=self._get_image(),
            _uid=req.content.uid,
            _userDir=req.content.userDir,
            host=host,
        )
        self.has_slot = False
        self.host.drivers[self.kind].append(self)
        self.instances[self.kind].append(self)

    @classmethod
    async def get_instance(cls, req):
        h = None
        for d in list(itertools.chain(*cls.instances.values())):
            # SECURITY: must only return instances for authorized user
            if d.uid == req.content.uid:
                if d.kind == req.kind:
                    return d
                # jobs of different kinds for the same user need to go to the
                # same host. Ex. sequential analysis jobs for parallel compute
                # jobs need to go to the same host to avoid NFS caching problems
#TODO(robnagler) what if there's already a driver of this kind later in the chain?
#  it seems like this needs to wait till the end.
                h = d.host
        if not h:
            h = min(cls.hosts.values(), key=lambda h: len(h.drivers[req.kind]))
        return cls(req, h)

    def free_slots(self):
        for d in self.host.drivers[self.kind]:
            if d.has_slot and not d.ops_pending_done:
                d.slot_free()

    @classmethod
    def init_class(cls):
        for k in job.KINDS:
            cls.instances[k] = []
        return cls

    def run_scheduler(self, exclude_self=False):
        self.free_slots()
#TODO(robnagler) might want to try all hosts, just so run_scheduler is generic
# it makes run_scheduler more of an auditor, and more robust if certain cases
# slip through this host-specific algorithm.
        h = self.host
        i = h.drivers[self.kind].index(self)
        # start iteration from index of current self to enable fair scheduling
        for d in h.drivers[self.kind][i:] + h.drivers[self.kind][:i]:
            if exclude_self and d == self:
                continue
            for o in d.get_ops_with_send_allocation():
                if not d.has_slot:
                    if h.slots[self.kind].in_use >= h.slots[self.kind].total:
                        continue
                    d.has_slot = True
                    h.slots[self.kind].in_use += 1
                assert o.opId not in d.ops_pending_done
                d.ops_pending_send.remove(o)
                d.ops_pending_done[o.opId] = o
                o.send_ready.set()

    async def kill(self):
        pkdlog('{}: stop cid={}', self.uid, self._cid)
        if '_cid' not in self:
            return
        await self._cmd(
            ('stop', '--time={}'.format(job_driver.KILL_TIMEOUT_SECS), self._cid),
        )
        self._cid = None

    def slot_free(self):
        if self.has_slot:
            self.host.slots[self.kind].in_use -= 1
            self.has_slot = False

    async def _agent_start(self, msg):
        self._agent_starting = True
        try:
            cmd, stdin, env = self._agent_cmd_stdin_env()
#TODO(robnagler) remove PKDict after https://github.com/radiasoft/pykern/issues/50
            c = PKDict(pykern.pkcollections.map_items(cfg[self.kind]))
            p = (
                'run',
                # attach to stdin for writing
                '--attach=stdin',
                '--cpus={}'.format(c.get('cores', 1)),
                '--init',
                # keeps stdin open so we can write to it
                '--interactive',
                '--memory={}g'.format(c.gigabytes),
                '--name={}'.format(self._cname),
                '--network=host',
                '--rm',
                '--ulimit=core=0',
                '--ulimit=nofile={}'.format(_MAX_OPEN_FILES),
                # do not use a "name", but a uid, because /etc/password is image specific, but
                # IDs are universal.
                '--user={}'.format(os.getuid()),
            ) + self._volumes() + (self._image,)
            self._cid = await self._cmd(p + cmd, stdin=stdin, env=env)
        except Exception as e:
            self._agent_starting = False
            pkdlog(
                'agentId={} exception={}',
                self._agentId,
                e,
                # TODO(e-carlin): read log
            )
            raise

    async def _cmd(self, cmd, stdin=subprocess.DEVNULL, env=None):
        c = DockerDriver.hosts[self.host.name].cmd_prefix + cmd
        pkdc('Running: {}', ' '.join(c))
        try:
            p = tornado.process.Subprocess(
                c,
                stdin=stdin,
                stdout=tornado.process.Subprocess.STREAM,
                stderr=subprocess.STDOUT,
                env=env,
            )
        finally:
            assert isinstance(stdin, io.BufferedRandom) or isinstance(stdin, int), \
                'type(stdin)={} expected io.BufferedRandom or int'.format(type(stdin))
            if isinstance(stdin, io.BufferedRandom):
                stdin.close()
        o = (await p.stdout.read_until_close()).decode('utf-8').rstrip()
        r = await p.wait_for_exit(raise_error=False)
        # TODO(e-carlin): more robust handling
        assert r == 0 , \
            '{}: failed: exit={} output={}'.format(c, r, o)
        return o

    #TODO(robnagler) probably should push this to pykern also in rsconf
    def _get_image(self):
        res = cfg.image
        if ':' in res:
            return res
        return res + ':' + pkconfig.cfg.channel

    def _volumes(self):
        res = []
        def _res(src, tgt):
            res.append('--volume={}:{}'.format(src, tgt))

        if cfg.dev_volumes:
            # POSIT: radiasoft/download/installers/rpm-code/codes.sh
            #   these are all the local environ directories.
            for v in '~/src', '~/.pyenv', '~/.local':
                v = pkio.py_path(v)
                # pyenv and src shouldn't be writable, only rundir
                _res(v, v + ':ro')
        # SECURITY: Must only mount the user's directory
        _res(self._userDir, self._userDir)
        return tuple(res)

    def _websocket_free(self):
        self.slot_free()
        self.run_scheduler(exclude_self=True)
        self.host.drivers[self.kind].remove(self)


def init_class():
    global cfg

    cfg = pkconfig.init(
        hosts=pkconfig.RequiredUnlessDev(tuple(), tuple, 'execution hosts'),
        image=('radiasoft/sirepo', str, 'docker image to run all jobs'),
        parallel=dict(
            cores=(1, int, 'cores per parallel job'),
            gigabytes=(1, int, 'gigabytes per parallel job'),
            slots_per_host=(1, int, 'parallel slots per node'),
        ),
        sequential=dict(
            gigabytes=(1, int, 'gigabytes per sequential job'),
            slots_per_host=(1, int, 'sequential slots per node'),
        ),
        tls_dir=pkconfig.RequiredUnlessDev(None, _cfg_tls_dir, 'directory containing host certs'),
        dev_volumes=(pkconfig.channel_in('dev'), bool, 'mount ~/.pyenv, ~/.local and ~/src for development'),
    )
    if not cfg.tls_dir or not cfg.hosts:
        _init_dev_hosts()
    _init_hosts()
    return DockerDriver.init_class()


def _cfg_tls_dir(value):
    res = pkio.py_path(value)
    assert res.check(dir=True), \
        'directory does not exist; value={}'.format(value)
    return res


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


def _init_dev_hosts():
    assert pkconfig.channel_in('dev')

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
        o = subprocess.check_output(['sudo', 'cat', '/etc/docker/tls/' + f]).decode('utf-8')
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
                total=cfg[k].slots_per_host,
            )
            DockerDriver.hosts[h].drivers[k] = []
    assert len(DockerDriver.hosts) > 0, \
        '{}: no docker hosts found in directory'.format(cfg.tls_d)
