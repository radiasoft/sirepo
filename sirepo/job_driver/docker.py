"""TODO(e-carlin): Doc

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern import pkconfig, pkio, pkcompat
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdlog, pkdexc, pkdc
from sirepo import job
from sirepo import job_driver
import asyncio
import io
import os
import re
import sirepo.const
import sirepo.util
import subprocess
import tornado.ioloop
import tornado.process

#: prefix all container names. Full format looks like: srj-p-uid
_CNAME_PREFIX = "srj"

#: separator for container names
_CNAME_SEP = "-"

#: parse cotnainer names. POSIT: matches _cname_join()
_CNAME_RE = re.compile(_CNAME_SEP.join(("^" + _CNAME_PREFIX, r"([a-z]+)", "(.+)")))

# default is unlimited so put some real constraint
# TODO(e-carlin): max open files for local or nersc?
_MAX_OPEN_FILES = 1024

#: All docker commands should be very fast, but set this high enough justify.
_DOCKER_CMD_TIMEOUT = 10


class DockerDriver(job_driver.DriverBase):
    cfg = None

    __hosts = PKDict()

    __users = PKDict()

    def __init__(self, op, host):
        super().__init__(op)
        self.update(
            _cname=self._cname_join(),
            _image=self._get_image(),
            _user_dir=pkio.py_path(op.msg.userDir),
            host=host,
        )
        host.instances[self.kind].append(self)
        self.cpu_slot_q = host.cpu_slot_q[self.kind]
        self.__users.setdefault(self.uid, PKDict())[self.kind] = self
        self._agent_exec_dir = self._user_dir.join(
            "agent-docker",
            self.host.name,
            self._cname,
        )
        pkio.unchecked_remove(self._agent_exec_dir)

    def docker_cmd_prefix(self):
        return self.__hosts[self.host.name].cmd_prefix

    @classmethod
    def get_instance(cls, op):
        # SECURITY: must only return instances for authorized user
        u = cls.__users.get(op.msg.uid)
        if u:
            d = u.get(op.kind)
            if d:
                return d
            # jobs of different kinds for the same user need to go to the
            # same host. Ex. sequential analysis jobs for parallel compute
            # jobs need to go to the same host to avoid NFS caching problems
            h = list(u.values())[0].host
        else:
            # least used host
            h = min(cls.__hosts.values(), key=lambda h: len(h.instances[op.kind]))
        return cls(op, h)

    @classmethod
    def init_class(cls, job_supervisor):
        cls.cfg = pkconfig.init(
            agent_starting_secs=(
                cls._AGENT_STARTING_SECS_DEFAULT + 3,
                int,
                "how long to wait for agent start",
            ),
            aux_volumes=(
                tuple(),
                tuple,
                "Additional volumes mounted in the container (ex. raydata)",
            ),
            constrain_resources=(True, bool, "apply --cpus and --memory constraints"),
            dev_volumes=(
                pkconfig.in_dev_mode(),
                bool,
                "mount ~/.pyenv, ~/.local and ~/src for development",
            ),
            gpus=(None, _cfg_gpus, "enable gpus"),
            hosts=pkconfig.RequiredUnlessDev(tuple(), tuple, "execution hosts"),
            idle_check_secs=pkconfig.ReplacedBy("sirepo.job_driver.idle_check_secs"),
            image=("radiasoft/sirepo", str, "docker image to run all jobs"),
            mpich_shm_clean_up=(False, bool, "mpich4 orphans shm; see sirepo#7741"),
            parallel=dict(
                cores=(2, int, "cores per parallel job"),
                gigabytes=(1, int, "gigabytes per parallel job"),
                shm_bytes=(
                    None,
                    pkconfig.parse_bytes,
                    "parallel shared memory size in bytes",
                ),
                slots_per_host=(1, int, "parallel slots per node"),
            ),
            sequential=dict(
                gigabytes=(1, int, "gigabytes per sequential job"),
                shm_bytes=(
                    None,
                    pkconfig.parse_bytes,
                    "sequential shared memory size in bytes",
                ),
                slots_per_host=(1, int, "sequential slots per node"),
            ),
            supervisor_uri=job.DEFAULT_SUPERVISOR_URI_DECL,
            tls_dir=pkconfig.RequiredUnlessDev(
                None, _cfg_tls_dir, "directory containing host certs"
            ),
        )
        if not cls.cfg.tls_dir or not cls.cfg.hosts:
            cls._init_dev_hosts()
        cls._init_hosts(job_supervisor)
        return cls

    async def kill(self):
        pkdlog("{} cid={:.12}", self, self.pkdel("_cid"))
        _, e = await _DockerCmd(
            cmd=(
                "stop",
                "--timeout={}".format(job_driver.KILL_TIMEOUT_SECS),
                self._cname,
            ),
            driver=self,
        ).start()
        # logging in _DockerCmd

    async def prepare_send(self, op):
        if op.op_name == job.OP_RUN:
            op.msg.mpiCores = self.cfg[self.kind].get("cores", 1)
        return await super().prepare_send(op)

    def _agent_env(self, op):
        return super()._agent_env(
            op,
            env=PKDict(
                SIREPO_PKCLI_JOB_AGENT_MPICH_SHM_CLEAN_UP=(
                    "1" if self.cfg.mpich_shm_clean_up else ""
                ),
            ),
        )

    def _cname_join(self):
        """Create a cname or cname_prefix from kind and uid

        POSIT: matches _CNAME_RE
        """
        return _CNAME_SEP.join([_CNAME_PREFIX, self.kind[0], self.uid])

    async def _do_agent_start(self, op):
        def _constrain_resources(cfg_kind):
            if not self.cfg.constrain_resources:
                return tuple()
            return (
                "--cpus={}".format(cfg_kind.get("cores", 1)),
                "--memory={}g".format(cfg_kind.gigabytes),
            )

        def _gpus():
            return (
                (f"--gpus={self.cfg.gpus}",) if self.cfg.gpus is not None else tuple()
            )

        def _shm_size(cfg_kind):
            return (
                (f"--shm-size={cfg_kind.shm_bytes}",)
                if cfg_kind.shm_bytes is not None
                else tuple()
            )

        cmd, stdin, _ = self._agent_cmd_stdin_env(op, cwd=self._agent_exec_dir)
        pkdlog("{} agent_exec_dir={}", self, self._agent_exec_dir)
        pkio.mkdir_parent(self._agent_exec_dir)
        c = self.cfg[self.kind]
        p = (
            (
                "create",
                "--init",
                # keeps stdin, stdout, stderr open
                "--interactive",
                f"--name={self._cname}",
                "--network=host",
                "--rm",
                "--ulimit=core=0",
                f"--ulimit=nofile={_MAX_OPEN_FILES}",
                # do not use a "name", but a uid, because /etc/password is image specific,
                # and we enforce uid's to be consistent in builds
                f"--user={os.getuid()}",
            )
            + _constrain_resources(c)
            + _shm_size(c)
            + _gpus()
            + self._volumes()
            + (self._image,)
        )
        self.driver_details.pkupdate(host=self.host.name)
        o, e = await _DockerCmd(cmd=p + cmd, driver=self).start()
        if e:
            # Logging in _DockerCmd
            return
        self._cid = o
        asyncio.create_task(
            _DockerCmd(
                cmd=("start", "--interactive", self._cid),
                driver=self,
                stdin=stdin,
                log_output=True,
                timeout=None,
            ).start(),
        )
        pkdlog("{} cname={} cid={:.12}", self, self._cname, self._cid)

    # TODO(robnagler) probably should push this to pykern also in rsconf
    def _get_image(self):
        res = self.cfg.image
        if ":" in res:
            return res
        return res + ":" + pkconfig.cfg.channel

    @classmethod
    def _init_dev_hosts(cls):
        assert pkconfig.in_dev_mode()

        from sirepo import srdb

        assert not (
            cls.cfg.tls_dir or cls.cfg.hosts
        ), "neither cfg.tls_dir and cfg.hosts nor must be set to get auto-config"
        # dev mode only; see _cfg_tls_dir and _cfg_hosts
        cls.cfg.tls_dir = srdb.root().join("docker_tls")
        cls.cfg.hosts = (sirepo.const.LOCALHOST_FQDN,)
        d = cls.cfg.tls_dir.join(cls.cfg.hosts[0])
        if d.check(dir=True):
            return
        pkdlog(
            "initializing docker dev env; initial docker pull will take a few minutes..."
        )
        d.ensure(dir=True)
        for f in "key.pem", "cert.pem":
            o = subprocess.check_output(["sudo", "cat", "/etc/docker/tls/" + f]).decode(
                "utf-8"
            )
            assert o.startswith(
                "-----BEGIN"
            ), "incorrect tls file={} content={}".format(f, o)
            d.join(f).write(o)
        # we just reuse the same cert as the docker server since it's local host
        d.join("cacert.pem").write(o)

    @classmethod
    def _init_hosts(cls, job_supervisor):
        def _cmd_prefix(host, tls_d):
            args = [
                "docker",
                # docker TLS port is hardwired
                "--host=tcp://{}:2376".format(host),
                "--tlsverify",
            ]
            # POSIT: rsconf.component.docker creates {cacert,cert,key}.pem
            for x in "cacert", "cert", "key":
                f = tls_d.join(x + ".pem")
                assert f.check(), "tls file does not exist for host={} file={}".format(
                    host, f
                )
                args.append("--tls{}={}".format(x, f))
            return tuple(args)

        for h in cls.cfg.hosts:
            d = cls.cfg.tls_dir.join(h)
            x = cls.__hosts[h] = PKDict(
                cmd_prefix=_cmd_prefix(h, d),
                instances=PKDict({k: [] for k in job.KINDS}),
                name=h,
                cpu_slot_q=PKDict(
                    {
                        k: job_supervisor.SlotQueue(cls.cfg[k].slots_per_host)
                        for k in job.KINDS
                    }
                ),
            )
        assert len(cls.__hosts) > 0, "{}: no docker hosts found in directory".format(
            cls.cfg.tls_d
        )

    def _volumes(self):
        res = []

        def _res(vol, mode=None):
            t = s = pkio.py_path(vol)
            if mode:
                t += f":{mode}"
            res.append("--volume={}:{}".format(s, t))

        if self.cfg.dev_volumes:
            # POSIT: radiasoft/download/installers/rpm-code/codes.sh
            #   these are all the local environ directories.
            for v in "~/src", "~/.pyenv", "~/.local":
                _res(v, mode="ro")
            for v in self.cfg.aux_volumes:
                _res(v)
        # SECURITY: Must only mount the user's directory
        _res(self._user_dir)
        return tuple(res)


CLASS = DockerDriver


class _DockerCmd(PKDict):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.pksetdefault(
            stdin=subprocess.DEVNULL,
            timeout=_DOCKER_CMD_TIMEOUT,
            log_output=False,
        )
        self.error_prefix = f"cmd={self.cmd[0]} cname={self.driver._cname}"
        self.stdout = ""
        self.stderr = ""
        self.timer = None
        self.return_code = None
        self.timed_out = False
        self.status_ready = asyncio.Event()
        self.output_ready = PKDict(stdout=asyncio.Event(), stderr=asyncio.Event())

    async def start(self):
        def _callbacks():
            f = self._log_output if self.log_output else self._read_output
            asyncio.create_task(f("stdout"))
            asyncio.create_task(f("stderr"))
            self.proc.set_exit_callback(self._on_exit)
            if self.timeout:
                self.timer = tornado.ioloop.IOLoop.current().call_later(
                    self.timeout, self._on_timeout
                )

        def _subprocess():
            self.cmd = self.driver.docker_cmd_prefix() + self.cmd
            pkdc("{} subprocess: {}", self.driver, " ".join(self.cmd))
            try:
                self.proc = tornado.process.Subprocess(
                    self.cmd,
                    stdin=self.stdin,
                    stdout=tornado.process.Subprocess.STREAM,
                    stderr=tornado.process.Subprocess.STREAM,
                )
            except Exception as e:
                pkdlog(
                    "{} subprocess failed error={} cmd={}",
                    self.error_prefix,
                    e,
                    self.cmd,
                )
                return None, str(e)
            finally:
                if hasattr(self.stdin, "close"):
                    self.stdin.close()

        _subprocess()
        _callbacks()
        await self.status_ready.wait()
        if self.timed_out:
            # This should not happen so use SIGKILL for expediency
            try:
                self.proc.proc.kill()
            except Exception:
                pass
            pkdlog("{} subprocess timed out cmd={}", self.error_prefix, self.cmd)
            return None, "error=subprocess timed out"
        elif self.timer:
            tornado.ioloop.IOLoop.current().remove_timeout(self.timer)
        e = "" if self.return_code == 0 else f"non-zero exit={self.return_code}"
        if self.log_output:
            pkdlog("{} error={} cmd={}", self.error_prefix, e, self.cmd)
            return (None, e)
        await self.output_ready.stderr.wait()
        await self.output_ready.stdout.wait()
        if self.return_code == 0:
            # Return None for zero exit
            return (self.stdout, None)
        if e:
            pkdlog(
                "{} error={} cmd={} stderr={}",
                self.error_prefix,
                e,
                self.cmd,
                self.stderr,
            )
        return (self.stdout, e)

    async def _log_output(self, which):
        def _write(buf):
            l = buf.splitlines()
            rv = l.pop() if buf[-1] == "\n" else ""
            for x in l:
                # Good enough for logging case, because only used with start
                pkdlog("{} {}", self.driver._cname, x)
            return rv

        s = getattr(self.proc, which)
        b = ""
        try:
            while True:
                b = _write(
                    b + pkcompat.from_bytes(await s.read_bytes(1000, partial=True))
                )
        except tornado.iostream.StreamClosedError:
            if b:
                pkdlog("{} {}", self.error_prefix, b)
        s.close()

    def _on_exit(self, return_code):
        self.return_code = return_code
        self.status_ready.set()

    def _on_timeout(self):
        self.timed_out = True
        self.status_ready.set()

    async def _read_output(self, which):
        self[which] = pkcompat.from_bytes(
            await getattr(self.proc, which).read_until_close()
        ).rstrip()
        self.output_ready[which].set()


def _cfg_gpus(value):
    if value != "all":
        pkconfig.raise_error("only accepts 'all' or empty string")
    return value


def _cfg_tls_dir(value):
    res = pkio.py_path(value)
    assert res.check(dir=True), "directory does not exist; value={}".format(value)
    return res
