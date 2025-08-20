"""TODO(e-carlin): Doc

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern import pkconfig
from pykern import pkio
from pykern import pkjson
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdlog, pkdexc
from sirepo import job
from sirepo import job_driver
from sirepo import util
import asyncio
import asyncssh
import asyncssh.process
import datetime
import errno
import sirepo.const
import sirepo.job_supervisor
import sirepo.simulation_db
import sirepo.util
import tornado.gen
import tornado.ioloop
import tornado.websocket
import urllib.parse

_RUN_DIR_OPS = job.SLOT_OPS.union((job.OP_RUN_STATUS,))


class SbatchDriver(job_driver.DriverBase):
    cfg = None

    _KNOWN_HOSTS = None

    __instances = PKDict()

    def __init__(self, op):
        def _op_queue_size(op_kind):
            return self.cfg.run_slots if op_kind == job.OP_RUN else 1

        super().__init__(op)
        self.pkupdate(
            # before it is overwritten by prepare_send
            _local_user_dir=pkio.py_path(op.msg.userDir),
            _srdb_root=None,
            # Allow self.cfg.run_slots and every other op type to
            # run (assume OP_RUN is one of SLOT_OPS). This
            # is essentially a no-op (sbatch constrains its own cpu
            # resources) but makes it easier to code the other cases.
            cpu_slot_q=sirepo.job_supervisor.SlotQueue(
                len(job.SLOT_OPS) + self.cfg.run_slots - 1,
            ),
            op_slot_q={
                k: sirepo.job_supervisor.SlotQueue(maxsize=_op_queue_size(k))
                for k in job.SLOT_OPS
            },
        )
        self.__instances[self.uid] = self

    async def free_resources(self, *args, **kwargs):
        try:
            self._srdb_root = None
        except Exception as e:
            pkdlog("{} error={} stack={}", self, e, pkdexc())
        return await super().free_resources(*args, **kwargs)

    async def kill(self):
        def _websocket_close():
            if (w := not self.get("_websocket")) is None:
                return
            try:
                # hopefully the agent is nice and listens to the kill
                w.write_message(PKDict(opName=job.OP_KILL))
            except tornado.websocket.WebSocketClosedError:
                self._websocket = None
                pkdlog("websocket closed {}", self)
            except Exception as e:
                pkdlog("{} error={} stack={}", self, e, pkdexc())

        _websocket_close()
        await self._ssh_close()

    @classmethod
    def get_instance(cls, op):
        u = op.msg.uid
        return cls.__instances.pksetdefault(u, lambda: cls(op))[u]

    @classmethod
    def init_class(cls, job_supervisor_module):
        global job_supervisor
        job_supervisor = job_supervisor_module
        cls.cfg = pkconfig.init(
            agent_log_read_sleep=(
                5,
                int,
                "how long to wait before reading the agent log on start",
            ),
            agent_starting_secs=(
                cls._AGENT_STARTING_SECS_DEFAULT * 3,
                int,
                "how long to wait for agent start",
            ),
            cores=(None, int, "dev cores config"),
            host=pkconfig.Required(str, "host name for slum controller"),
            host_key=pkconfig.Required(str, "host key"),
            nodes=(None, int, "dev nodes config"),
            run_slots=(1, int, "number of concurrent OP_RUN for each user"),
            shifter_image=(None, str, "needed if using Shifter"),
            sirepo_cmd=pkconfig.Required(str, "how to run sirepo"),
            srdb_root=pkconfig.Required(
                _cfg_srdb_root, "where to run job_agent, must include {sbatch_user}"
            ),
            supervisor_uri=job.DEFAULT_SUPERVISOR_URI_DECL,
            want_persistent_ssh=(False, bool, "maintain ssh connection and forward supervisor via unix domain socket"),
        )
        cls._KNOWN_HOSTS = (
            cls.cfg.host_key
            if cls.cfg.host in cls.cfg.host_key
            else "{} {}".format(cls.cfg.host, cls.cfg.host_key)
        ).encode("ascii")
        return cls

    def op_is_untimed(self, op):
        return True

    async def prepare_send(self, op):
        def _add_dirs(msg):
            msg.userDir = "/".join(
                (
                    self._srdb_root,
                    sirepo.simulation_db.USER_ROOT_DIR,
                    self.uid,
                )
            )
            msg.runDir = "/".join((msg.userDir, msg.simulationType, msg.computeJid))
            return msg

        m = op.msg
        c = m.pkdel("sbatchCredentials")
        if self._srdb_root is None or c:
            if c:
                self._creds = c
            self._assert_creds(m)
            self._srdb_root = self.cfg.srdb_root.format(
                sbatch_user=self._creds.username,
            )
        if op.op_name in _RUN_DIR_OPS:
            _add_dirs(m)
            if op.op_name == job.OP_RUN and op.msg.jobCmd == job.CMD_COMPUTE:
                assert m.sbatchHours
                for f, c in [
                    ["sbatchCores", self.cfg.cores],
                    ["sbatchNodes", self.cfg.nodes],
                ]:
                    if f in m and c:
                        m[f] = min(m[f], c)
                m.mpiCores = m.sbatchCores
            m.shifterImage = self.cfg.shifter_image
        return await super().prepare_send(op)

    def _agent_env(self, op, ctx):
        return super()._agent_env(
            op,
            env=PKDict(
                SIREPO_PKCLI_JOB_AGENT_SUPERVISOR_UNIX_PATH=ctx.forward_remote_path,
                SIREPO_SRDB_ROOT=self._srdb_root,
            ),
        )

    def _assert_creds(self, msg):
        if not self.get("_creds") or "username" not in self._creds:
            self._raise_sbatch_login_srexception("no-creds", msg)

    async def _do_agent_start(self, op):

        def _agent_start_dev():
            if not pkconfig.in_dev_mode():
                return ""
            res = ""
            if self.cfg.shifter_image:
                res += (
                    "\n".join(
                        f"(cd {sirepo.const.DEV_SRC_RADIASOFT_DIR}/{p} && git pull -q || true)"
                        for p in ("pykern", "sirepo")
                    )
                    + "\n"
                )
            return res

        def _ctx():
            s = self._srdb_root
            rv = PKDict(
                forward_remote_path=s + "/supervisor.sock" if self.cfg.want_persistent_ssh else "",
                log_path=s + "/job_agent.log"
                msg=op.msg
                start_dir=s,
            )
            if pkconfig.in_dev_mode():
                pkdlog("agent_log={}", rv.log_path)
            return rv

        def _creds():
            self._assert_creds(op.msg)
            return PKDict(
                known_hosts=self._KNOWN_HOSTS,
                password=(
                    self._creds.password + self._creds.otp
                    if "nersc" in self.cfg.host
                    else self._creds.password
                ),
                username=self._creds.username,
            )

        async def _forward_remote_path(ctx):
            if not self.cfg.want_persistent_ssh:
                return
            try:
                async with self._ssh.create_process(
                    f"rm -f '{ctx.forward_remote_path}'",
                    stderr=asyncssh.process.DEVNULL,
                    stdin=asyncssh.process.DEVNULL,
                    stdout=asyncssh.process.DEVNULL,
                ) as p:
                    p.communicate()
            except Exception as e:
                pkdlog("rm file={} error={}; continuing", ctx.ctx.forward_remote_path, e)
            u = urllib.parse.urlparse(self.cfg.supervisor_uri)
            if (p := u.port) is None:
                p = 443 if u.scheme == 'https' else 80
            self._ssh_forward = await self._ssh.forward_remote_path_to_port(ctx.forward_remote_path, u.hostname, p)

        async def _get_agent_log(cfg, before_start=True):
            try:
                if not before_start:
                    await tornado.gen.sleep(self.cfg.agent_log_read_sleep)
                async with self._ssh.create_process(
                    # test is a shell-builtin so no abs path. tail varies in
                    # location. can trust that it will be in the path
                    f"test -e {cfg.log_path} && tail --lines=200 {f}"
                ) as p:
                    o, e = await p.communicate()
                    _write_to_log(
                        o, e, f"remote-{'before' if before_start else 'after'}-start"
                    )
            except Exception as e:
                pkdlog(
                    "{} e={} stack={}",
                    self,
                    e,
                    pkdexc(),
                )

        def _write_to_log(stdout, stderr, filename):
            p = pkio.py_path(self._local_user_dir).join("agent-sbatch", self.cfg.host)
            pkio.mkdir_parent(p)
            f = p.join(
                f'{datetime.datetime.now().strftime("%Y%m%d%H%M%S")}-{filename}.log'
            )
            r = pkjson.dump_pretty(PKDict(stdout=stdout, stderr=stderr, filename=f), f)
            if pkconfig.in_dev_mode():
                pkdlog(r)

        c = _ctx()
        script = f"""#!/bin/bash
set -euo pipefail
{_agent_start_dev()}
mkdir -p '{c.start_dir}'
cd '{c.start_dir}'
{self._agent_env(op, c)}
(/usr/bin/env; setsid {self.cfg.sirepo_cmd} job_agent start_sbatch) &>> {c.log_path} &
disown
"""
        try:
            self._ssh = await asyncssh.connect(self.cfg.host, **_creds())
            await _forward_remote_path(c)
            async with self._ssh.create_process("/bin/bash --noprofile --norc -l") as p:
                await _get_agent_log(c, before_start=True)
                o, e = await p.communicate(input=script)
                if o or e:
                    _write_to_log(o, e, "start")
            self.driver_details.pkupdate(
                host=self.cfg.host,
                username=self._creds.username,
            )
            await _get_agent_log(c, before_start=False)
        except Exception as e:
            pkdlog("error={} stack={}", e, pkdexc())
            self._ssh_close()
            self._srdb_root = None
            self._raise_sbatch_login_srexception(
                (
                    "invalid-creds"
                    if isinstance(e, asyncssh.misc.PermissionDenied)
                    else "general-connection-error"
                ),
                c.msg,
            )
        finally:
            self.pkdel("_creds")
            if not self.cfg.want_persistent_ssh:
                self._ssh_close()

    def _raise_sbatch_login_srexception(self, reason, msg):
        raise util.SRException(
            "sbatchLogin",
            PKDict(
                isModal=True,
                isSbatchLogin=True,
                reason=reason,
                computeModel=msg.computeModel,
                simulationId=msg.simulationId,
            ),
        )

    async def _ssh_close():
        for a in "_ssh_forward", "_ssh":
            if (c := getattr(self, a, None)) is None:
                continue
            setattr(self, a, None)
            try:
                c.close()
                await c.wait_close()
            except Exception as e:
                pkdlog("attr={} {} error={} stack={}", a, self, e, pkdexc())

    def _start_idle_timeout(self):
        """Sbatch agents should be kept alive as long as possible"""
        pass


CLASS = SbatchDriver


def _cfg_srdb_root(value):
    assert "{sbatch_user}" in value, "must include {sbatch_user} in string"
    return value
