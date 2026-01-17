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

#: Enterprise is the only special plan so just say default. Not sent to user, just for log msgs
_DEFAULT_PLAN = "default"
_ENTERPRISE_PLAN = sirepo.auth_role.ROLE_PLAN_ENTERPRISE

# do not use a "name", but a uid, because /etc/password is image specific,
# and we enforce uid's to be consistent in builds
_PROCESS_USER_ID = os.getuid()


class DockerDriver(job_driver.DriverBase):
    cfg = None

    __hosts = PKDict()

    __users = PKDict()

    def __init__(self, op, host):
        def _cname_join():
            # POSIT: matches _CNAME_RE
            return _CNAME_SEP.join([_CNAME_PREFIX, self.kind[0], self.uid])

        super().__init__(op)
        self.update(
            _cname=_cname_join(),
            _user_dir=pkio.py_path(op.msg.userDir),
            host=host,
        )
        host.kinds[self.kind].instances.append(self)
        self.cpu_slot_q = host.kinds[self.kind].cpu_slot_q
        self.__users.setdefault(self.uid, PKDict())[self.kind] = self
        self._agent_exec_dir = self._user_dir.join(
            "agent-docker",
            self.host.name,
            self._cname,
        )
        pkio.unchecked_remove(self._agent_exec_dir)

    async def free_resources(self, *args, **kwargs):
        # TODO(robnagler) free_resources does the kill, which is problematic
        await super().free_resources(*args, **kwargs)
        if self.host is None:
            return
        try:
            h = self.host
            self.host = None
            h.kinds[self.kind].instances.remove(self)
            self.__users[self.uid].pkdel(self.kind)
            if not self.__users[self.uid]:
                self.__users.pkdel(self.uid)
        except Exception as e:
            pkdlog("{} error={} stack={}", self, e, pkdexc())
        return

    @classmethod
    def get_instance(cls, op):
        def _hosts():
            if op.msg.activePlan == _ENTERPRISE_PLAN and (
                rv := cls.__hosts[_ENTERPRISE_PLAN].values()
            ):
                return rv
            if rv := cls.__hosts[_DEFAULT_PLAN].values():
                return rv
            raise AssertionError(f"no hosts for plan={op.msg.activePlan}")

        # SECURITY: must only return instances for authorized user
        u = cls.__users.get(op.msg.uid)
        if u:
            d = u.get(op.kind)
            if d:
                return d
            # jobs of different kinds for the same user need to go to the
            # same host. Ex. sequential analysis jobs for parallel compute
            # jobs need to go to the same host to avoid NFS caching problems.
            h = list(u.values())[0].host
        else:
            # least used host
            h = min(_hosts(), key=lambda h: len(h.kinds[op.kind].instances))
        return cls(op, h)

    @classmethod
    def init_class(cls, job_supervisor):
        def _image():
            rv = cls.cfg.image
            return rv if ":" in rv else (rv + ":" + pkconfig.cfg.channel)

        def _plan_cfg(plan):
            return PKDict(
                constrain_resources=(
                    True,
                    bool,
                    f"{plan} apply --cpus and --memory constraints",
                ),
                hosts=((), tuple, f"{plan} parallel and sequential hosts"),
                parallel=PKDict(
                    cores=(
                        2,
                        pkconfig.parse_positive_int,
                        f"{plan} cores per parallel job",
                    ),
                    gigabytes=(
                        1,
                        pkconfig.parse_positive_int,
                        f"{plan} gigabytes per parallel job",
                    ),
                    gpus=(None, _cfg_gpus, f"{plan} enable gpus"),
                    shm_bytes=(
                        None,
                        pkconfig.parse_bytes,
                        f"{plan} parallel shared memory size in bytes",
                    ),
                    slots_per_host=(
                        1,
                        pkconfig.parse_positive_int,
                        f"{plan} parallel slots per node",
                    ),
                ),
                sequential=PKDict(
                    gigabytes=(
                        1,
                        pkconfig.parse_positive_int,
                        f"{plan} gigabytes per sequential job",
                    ),
                    shm_bytes=(
                        None,
                        pkconfig.parse_bytes,
                        f"{plan} sequential shared memory size in bytes",
                    ),
                    slots_per_host=(
                        1,
                        pkconfig.parse_positive_int,
                        f"{plan} sequential slots per node",
                    ),
                ),
            )

        b = PKDict(
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
            dev_volumes=(
                pkconfig.in_dev_mode(),
                bool,
                "mount ~/.pyenv, ~/.local and ~/src for development",
            ),
            enterprise=_plan_cfg(_ENTERPRISE_PLAN),
            image=("radiasoft/sirepo", str, "docker image to run all jobs"),
            mpich_shm_clean_up=(False, bool, "mpich4 orphans shm; see sirepo#7741"),
            supervisor_uri=job.DEFAULT_SUPERVISOR_URI_DECL,
            tls_dir=pkconfig.RequiredUnlessDev(
                None, _cfg_tls_dir, "directory containing host certs"
            ),
        ).pkupdate(_plan_cfg(_DEFAULT_PLAN))
        cls.cfg = pkconfig.init(**b)
        if not cls.cfg.tls_dir or not (cls.cfg.hosts or cls.enterprise.hosts):
            cls._init_dev_hosts()
        cls._init_hosts(job_supervisor)
        cls._image = _image()
        return cls

    async def kill(self):
        # Protect against kills after free_resources
        if self.host is None:
            return
        pkdlog("{} cid={:.12}", self, self.pkdel("_cid"))
        _, e = await _DockerCmd(
            cmd=(
                "stop",
                "--timeout={}".format(job_driver.KILL_TIMEOUT_SECS),
                # may have been started by previous invocation of supervisor
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

    async def _do_agent_start(self, op):
        def _create():
            return self.host.kinds[self.kind].create_prefix + (
                # SECURITY: Must only mount the user's directory
                self._volume_arg(self._user_dir),
                f"--name={self._cname}",
                self._image,
            )

        cmd, stdin, _ = self._agent_cmd_stdin_env(op, cwd=self._agent_exec_dir)
        pkdlog("{} agent_exec_dir={}", self, self._agent_exec_dir)
        pkio.mkdir_parent(self._agent_exec_dir)
        self.driver_details.pkupdate(host=self.host.name)
        o, e = await _DockerCmd(cmd=_create() + cmd, driver=self).start()
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
        def _host(host, plan_cfg):
            return PKDict(
                cmd_prefix=_host_cmd_prefix(host, cls.cfg.tls_dir.join(host)),
                name=host,
                kinds=PKDict({k: _kind(k, plan_cfg, plan_cfg[k]) for k in job.KINDS}),
            )

        def _host_cmd_prefix(host, tls_d):
            args = [
                "docker",
                # docker TLS port is hardwired
                "--host=tcp://{}:2376".format(host),
                "--tlsverify",
            ]
            # POSIT: rsconf.component.docker creates {cacert,cert,key}.pem
            for x in "cacert", "cert", "key":
                f = tls_d.join(x + ".pem")
                if not f.check():
                    raise AssertionError(
                        f"tls file does not exist for host={host} file={f}"
                    )
                args.append("--tls{}={}".format(x, f))
            return tuple(args)

        def _kind(kind, plan_cfg, kind_cfg):
            return PKDict(
                cpu_slot_q=job_supervisor.SlotQueue(kind_cfg.slots_per_host),
                instances=[],
                kind_cfg=kind_cfg,
                create_prefix=_kind_create_prefix(plan_cfg, kind_cfg),
            )

        def _kind_create_prefix(plan_cfg, kind_cfg):
            def _volumes():
                rv = []
                if cls.cfg.dev_volumes:
                    # POSIT: radiasoft/download/installers/rpm-code/codes.sh
                    #   these are all the local environ directories.
                    for v in "~/src", "~/.pyenv", "~/.local":
                        rv.append(cls._volume_arg(v, mode="ro"))
                    for v in cls.cfg.aux_volumes:
                        rv.append(cls._volume_arg(v))
                return tuple(rv)

            rv = [
                "create",
                "--init",
                # keeps stdin, stdout, stderr open
                "--interactive",
                "--network=host",
                "--rm",
                "--ulimit=core=0",
                f"--ulimit=nofile={_MAX_OPEN_FILES}",
                f"--user={_PROCESS_USER_ID}",
            ]
            if plan_cfg.constrain_resources:
                rv.extend(
                    (
                        f"--cpus={kind_cfg.get('cores', 1)}",
                        f"--memory={kind_cfg.gigabytes}g",
                    )
                )
            if g := kind_cfg.get("gpus"):
                rv.append(f"--gpus={g}")
            if kind_cfg.shm_bytes:
                rv.append(f"--shm-size={kind_cfg.shm_bytes}")
            rv.extend(_volumes())
            return tuple(rv)

        def _plan(hosts, plan_cfg):
            return PKDict({h: _host(h, plan_cfg) for h in plan_cfg.hosts})

        x = PKDict()
        for p, c in (
            (_DEFAULT_PLAN, cls.cfg),
            (_ENTERPRISE_PLAN, cls.cfg.enterprise),
        ):
            x[p] = set(c.hosts)
            if c.hosts:
                cls.__hosts[p] = _plan(c.hosts, c)
        if len(x[_ENTERPRISE_PLAN]) + len(x[_DEFAULT_PLAN]) == 0:
            raise AssertionError("no docker hosts")
        if d := x[_ENTERPRISE_PLAN].intersection(x[_DEFAULT_PLAN]):
            raise AssertionError("enterprise and default docker hosts overlap={d}")

    @classmethod
    def _volume_arg(cls, vol, mode=None):
        v = pkio.py_path(vol)
        rv = f"--volume={v}:{v}"
        if mode:
            rv += f":{mode}"
        return rv


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
            self.cmd = self.driver.host.cmd_prefix + self.cmd
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
