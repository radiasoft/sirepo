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

    cfg = None

    __hosts = PKDict()

    __users = PKDict()

    def __init__(self, req, host):
        super().__init__(req)
        self.update(
            _cname=self._cname_join(),
            _idle_timer=None,
            _image=self._get_image(),
            _user_dir=pkio.py_path(req.content.userDir),
            host=host,
        )
        host.instances[self.kind].append(self)
        self.cpu_slot_q = host.cpu_slot_q[self.kind]
        self.__users.setdefault(self.uid, PKDict())[self.kind] = self
        self._agent_exec_dir = self._user_dir.join(
            'agent-docker',
            self.host.name,
            self._cname,
        )
        pkio.unchecked_remove(self._agent_exec_dir)

    def cpu_slot_peers(self):
        return self.host.instances[self.kind]

    @classmethod
    def get_instance(cls, req):
        # SECURITY: must only return instances for authorized user
        u = cls.__users.get(req.content.uid)
        if u:
            d = u.get(req.kind)
            if d:
                return d
            # jobs of different kinds for the same user need to go to the
            # same host. Ex. sequential analysis jobs for parallel compute
            # jobs need to go to the same host to avoid NFS caching problems
            h = list(u.values())[0].host
        else:
            # least used host
            h = min(cls.__hosts.values(), key=lambda h: len(h.instances[req.kind]))
        return cls(req, h)

    @classmethod
    def init_class(cls):
        cls.cfg = pkconfig.init(
            agent_starting_secs=(
                cls._AGENT_STARTING_SECS,
                int,
                'how long to wait for agent start',
            ),
            dev_volumes=(pkconfig.channel_in('dev'), bool, 'mount ~/.pyenv, ~/.local and ~/src for development'),
            hosts=pkconfig.RequiredUnlessDev(tuple(), tuple, 'execution hosts'),
            idle_check_secs=(1800, int, 'how many seconds to wait between checks'),
            image=('radiasoft/sirepo', str, 'docker image to run all jobs'),
            parallel=dict(
                cores=(2, int, 'cores per parallel job'),
                gigabytes=(1, int, 'gigabytes per parallel job'),
                slots_per_host=(1, int, 'parallel slots per node'),
            ),
            sequential=dict(
                gigabytes=(1, int, 'gigabytes per sequential job'),
                slots_per_host=(1, int, 'sequential slots per node'),
            ),
            supervisor_uri=job.DEFAULT_SUPERVISOR_URI_DECL,
            tls_dir=pkconfig.RequiredUnlessDev(None, _cfg_tls_dir, 'directory containing host certs'),
        )
        if not cls.cfg.tls_dir or not cls.cfg.hosts:
            cls._init_dev_hosts()
        cls._init_hosts()
        return cls

    async def kill(self):
        c = self.get('_cid')
        self._cid = None
        pkdlog('{} cid={:.12}', self, c)
        try:
            await self._cmd(
                (
                    'stop',
                    '--time={}'.format(job_driver.KILL_TIMEOUT_SECS),
                    self._cname
                ),
            )
        except Exception as e:
            if not c and 'No such container' in str(e):
                # Make kill response idempotent
                return
            pkdlog('{} error={} stack={}', self, e, pkdexc())

    async def prepare_send(self, op):
        if op.opName == job.OP_RUN:
            op.msg.mpiCores = self.cfg[self.kind].get('cores', 1)
        return await super().prepare_send(op)

    @classmethod
    def _cmd_prefix(cls, host, tls_d):
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
                'tls file does not exist for host={} file={}'.format(host, f)
            args.append('--tls{}={}'.format(x, f))
        return tuple(args)

    def _cname_join(self):
        """Create a cname or cname_prefix from kind and uid

        POSIT: matches _CNAME_RE
        """
        return _CNAME_SEP.join([_CNAME_PREFIX, self.kind[0], self.uid])

    async def _do_agent_start(self, op):
        cmd, stdin, env = self._agent_cmd_stdin_env(cwd=self._agent_exec_dir)
        pkdlog('{} agent_exec_dir={}', self, self._agent_exec_dir)
        pkio.mkdir_parent(self._agent_exec_dir)
        c = self.cfg[self.kind]
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
        self.driver_details.pkupdate(host=self.host.name)
        pkdlog('{} cname={} cid={:.12}', self, self._cname, self._cid)

    async def _cmd(self, cmd, stdin=subprocess.DEVNULL, env=None):
        c = self.__hosts[self.host.name].cmd_prefix + cmd
        pkdc('{} running: {}', self, ' '.join(c))
        try:
            p = tornado.process.Subprocess(
                c,
                stdin=stdin,
                stdout=tornado.process.Subprocess.STREAM,
                stderr=subprocess.STDOUT,
                env=env,
            )
        except Exception as e:
            pkdlog('{} error={} cmd={} stack={}', self, e, c, pkdexc())
        finally:
            assert isinstance(stdin, io.BufferedRandom) or isinstance(stdin, int), \
                'type(stdin)={} expected io.BufferedRandom or int'.format(type(stdin))
            if isinstance(stdin, io.BufferedRandom):
                stdin.close()
        o = (await p.stdout.read_until_close()).decode('utf-8').rstrip()
        r = await p.wait_for_exit(raise_error=False)
        # TODO(e-carlin): more robust handling
        assert r == 0, \
            '{}: failed: exit={} output={}'.format(c, r, o)
        return o

    #TODO(robnagler) probably should push this to pykern also in rsconf
    def _get_image(self):
        res = self.cfg.image
        if ':' in res:
            return res
        return res + ':' + pkconfig.cfg.channel

    @classmethod
    def _init_dev_hosts(cls):
        assert pkconfig.channel_in('dev')

        from sirepo import srdb
        assert not (cls.cfg.tls_dir or cls.cfg.hosts), \
            'neither cfg.tls_dir and cfg.hosts nor must be set to get auto-config'
        # dev mode only; see _cfg_tls_dir and _cfg_hosts
        cls.cfg.tls_dir = srdb.root().join('docker_tls')
        cls.cfg.hosts = ('localhost.localdomain',)
        d = cls.cfg.tls_dir.join(cls.cfg.hosts[0])
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

    @classmethod
    def _init_hosts(cls):
        for h in cls.cfg.hosts:
            d = cls.cfg.tls_dir.join(h)
            x = cls.__hosts[h] = PKDict(
                cmd_prefix=cls._cmd_prefix(h, d),
                instances=PKDict(),
                name=h,
                cpu_slots=PKDict(),
                cpu_slot_q=PKDict(),
            )
            for k in job.KINDS:
                x.cpu_slot_q[k] = cls.init_q(cls.cfg[k].slots_per_host)
                x.instances[k] = []
        assert len(cls.__hosts) > 0, \
            '{}: no docker hosts found in directory'.format(cls.cfg.tls_d)

    def _receive_alive(self, msg):
        self._start_idle_timeout()
        super()._receive_alive(msg)

    def _start_idle_timeout(self):
        async def _kill_if_idle():
            if not self.ops:
                pkdlog('{}', self)
                self._idle_timer = None
                await self.kill()
            else:
                self._start_idle_timeout()

        if not self._idle_timer:
            self._idle_timer = tornado.ioloop.IOLoop.current().call_later(
                self.cfg.idle_check_secs,
                _kill_if_idle,
            )

    def _volumes(self):
        res = []
        def _res(src, tgt):
            res.append('--volume={}:{}'.format(src, tgt))

        if self.cfg.dev_volumes:
            # POSIT: radiasoft/download/installers/rpm-code/codes.sh
            #   these are all the local environ directories.
            for v in '~/src', '~/.pyenv', '~/.local':
                v = pkio.py_path(v)
                # pyenv and src shouldn't be writable, only rundir
                _res(v, v + ':ro')
        # SECURITY: Must only mount the user's directory
        _res(self._user_dir, self._user_dir)
        return tuple(res)


def init_class():
    return DockerDriver.init_class()


def _cfg_tls_dir(value):
    res = pkio.py_path(value)
    assert res.check(dir=True), \
        'directory does not exist; value={}'.format(value)
    return res
