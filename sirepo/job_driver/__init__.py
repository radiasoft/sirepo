"""Base for drivers

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern import pkconfig, pkinspect, pkconfig, pkjson
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdlog, pkdc, pkdexc, pkdformat
from sirepo import job
import importlib
import os
import pykern.pkio
import re
import sirepo.auth
import sirepo.const
import sirepo.events
import sirepo.feature_config
import sirepo.global_resources
import sirepo.sim_db_file
import sirepo.simulation_db
import sirepo.tornado
import sirepo.util
import tornado.ioloop
import tornado.locks


KILL_TIMEOUT_SECS = 3

#: map of driver names to class
_CLASSES = None

#: default class when not determined by op
_DEFAULT_CLASS = None

_DEFAULT_MODULE = "local"

_cfg = None

_UNTIMED_OPS = frozenset(
    (job.OP_ALIVE, job.OP_CANCEL, job.OP_ERROR, job.OP_KILL, job.OP_OK)
)


class AgentMsg(PKDict):
    async def receive(self):
        # Agent messages do not block the supervisor
        DriverBase.receive(self)


def assign_instance_op(op):
    m = op.msg
    if m.jobRunMode == job.SBATCH:
        res = _CLASSES[job.SBATCH].get_instance(op)
    else:
        res = _DEFAULT_CLASS.get_instance(op)
    if m.uid != res.uid:
        raise AssertionError(
            f"op.msg.uid={m.uid} is not same as db.uid={res.uid} for jid={m.get('computeJid')}",
        )
    return res


class DriverBase(PKDict):
    __instances = PKDict()

    _AGENT_STARTING_SECS_DEFAULT = 5

    def __init__(self, op):
        super().__init__(
            driver_details=PKDict({"type": self.__class__.__name__}),
            kind=op.kind,
            # TODO(robnagler) sbatch could override OP_RUN, but not OP_ANALYSIS
            # because OP_ANALYSIS touches the directory sometimes. Reasonably
            # there should only be one OP_ANALYSIS running on an agent at one time.
            op_slot_q=PKDict({k: job_supervisor.SlotQueue() for k in job.SLOT_OPS}),
            uid=op.msg.uid,
            _agent_id=sirepo.util.unique_key(),
            _agent_life_change_lock=tornado.locks.Lock(),
            _idle_timer=None,
            _prepared_sends=PKDict(),
            _websocket=None,
            _websocket_ready=sirepo.tornado.Event(),
            _websocket_ready_timeout=None,
        )
        self._sim_db_file_token = sirepo.sim_db_file.SimDbServer.token_for_user(
            self.uid
        )
        self._global_resources_token = (
            sirepo.global_resources.api.Req.token_for_user(self.uid)
            # TODO(e-carlin): we need a more grangular system to decide when to add this information
            if sirepo.feature_config.cfg().enable_global_resources
            else None
        )
        # Drivers persist for the life of the program so they are never removed
        self.__instances[self._agent_id] = self
        pkdlog("{}", self)

    def agent_is_ready_or_starting(self):
        return self._websocket_ready.is_set() or bool(self._websocket_ready_timeout)

    def destroy_op(self, op):
        """Remove op from our list of sends"""
        self._prepared_sends.pkdel(op.op_id)

    async def free_resources(self, caller):
        """Remove holds on all resources and remove self from data structures"""
        try:
            async with self._agent_life_change_lock:
                await self.kill()
                self._websocket_ready_timeout_cancel()
                self._websocket_ready.clear()
                self._websocket_close()
                e = f"job_driver.free_resources caller={caller}"
                for o in list(self._prepared_sends.values()):
                    o.destroy(internal_error=e)
        except Exception as e:
            pkdlog("{} caller={} error={} stack={}", self, caller, e, pkdexc())

    async def kill(self):
        raise NotImplementedError(
            "DriverBase subclasses need to implement their own kill",
        )

    def op_is_untimed(self, op):
        return op.op_name in _UNTIMED_OPS

    def pkdebug_str(self):
        return pkdformat(
            "{}(a={:.4} k={} u={:.4} {})",
            self.__class__.__name__,
            self._agent_id,
            self.kind,
            self.uid,
            list(self._prepared_sends.values()),
        )

    async def prepare_send(self, op):
        """Awaits agent ready and slots for sending.

        Agent is guaranteed to be ready and all slots are allocated
        upon return, if True.

        Returns:
            bool: False, op is destroyed
        """

        # If the agent is not ready after awaiting on slots, we need
        # to recheck the agent, because agent can die (asynchronously) at any point
        # while waiting for slots.
        if not await self._agent_ready(op):
            return False
        r = await self._slots_ready(op)
        if r == job_supervisor.SlotAllocStatus.OP_IS_DESTROYED:
            return False
        if r == job_supervisor.SlotAllocStatus.HAD_TO_AWAIT:
            if not await self._agent_ready(op):
                return False
        elif r != job_supervisor.SlotAllocStatus.DID_NOT_AWAIT:
            raise AssertionError(f"slots_ready invalid return={r}")
        self._prepared_sends[op.op_id] = op
        return True

    @classmethod
    def receive(cls, msg):
        """Receive message from agent"""
        a = cls.__instances.get(msg.content.agentId)
        if a:
            a._agent_receive(msg)
            return
        pkdlog("unknown agent, sending kill; msg={}", msg)
        try:
            msg.handler.write_message(PKDict(opName=job.OP_KILL), binary=True)
        except tornado.websocket.WebSocketClosedError:
            pkdlog("websocket closed {} from unknown agent", self)
        except Exception as e:
            pkdlog("error={} stack={}", e, pkdexc())

    def send(self, op):
        pkdlog("{} {} runDir={}", self, op, op.msg.get("runDir"))
        try:
            self._websocket.write_message(pkjson.dump_bytes(op.msg), binary=True)
            return True
        except tornado.websocket.WebSocketClosedError:
            pkdlog("websocket closed op={}", op)
        except Exception as e:
            pkdlog("error={} op={} stack={}", e, op, pkdexc())
        return False

    @classmethod
    async def terminate(cls):
        for d in list(cls.__instances.values()):
            try:
                # TODO(robnagler) need timeout
                await d.kill()
            except Exception as e:
                # If one kill fails still try to kill the rest
                pkdlog("error={} stack={}", e, pkdexc())

    def _websocket_close(self):
        w = self._websocket
        self._websocket = None
        if w:
            # Will not call websocket_on_close()
            w.sr_close()

    def websocket_on_close(self):
        pkdlog("{}", self)
        self._websocket = None
        self._start_free_resources(caller="websocket_on_close")

    def _websocket_ready_timeout_cancel(self):
        if self._websocket_ready_timeout:
            tornado.ioloop.IOLoop.current().remove_timeout(
                self._websocket_ready_timeout
            )
            self._websocket_ready_timeout = None

    async def _websocket_ready_timeout_handler(self):
        try:
            if not self._websocket_ready_timeout or self._websocket_ready.is_set():
                pkdlog("ignore timeout {}, is canceled or ready", self)
                return
            self._websocket_ready_timeout = None
            pkdlog("{} timeout={}", self, self.cfg.agent_starting_secs)
            self._start_free_resources(caller="_websocket_ready_timeout_handler")
        except Exception as e:
            pkdlog("exception={} stack={}", e, pkdexc())

    def _agent_cmd_stdin_env(self, op, **kwargs):
        return job.agent_cmd_stdin_env(
            ("sirepo", "job_agent", "start"),
            env=self._agent_env(op),
            uid=self.uid,
            **kwargs,
        )

    def _agent_env(self, op, env=None):
        return job.agent_env(
            env=(env or PKDict()).pksetdefault(
                PYKERN_PKDEBUG_WANT_PID_TIME="1",
                SIREPO_PKCLI_JOB_AGENT_AGENT_ID=self._agent_id,
                # POSIT: same as pkcli.job_agent.start
                SIREPO_PKCLI_JOB_AGENT_DEV_SOURCE_DIRS=os.environ.get(
                    "SIREPO_PKCLI_JOB_AGENT_DEV_SOURCE_DIRS",
                    str(pkconfig.in_dev_mode()),
                ),
                SIREPO_PKCLI_JOB_AGENT_GLOBAL_RESOURCES_SERVER_TOKEN=self._global_resources_token,
                SIREPO_PKCLI_JOB_AGENT_GLOBAL_RESOURCES_SERVER_URI=f"{self.cfg.supervisor_uri}{job.GLOBAL_RESOURCES_URI}",
                SIREPO_PKCLI_JOB_AGENT_START_DELAY=str(op.get("_agent_start_delay", 0)),
                SIREPO_PKCLI_JOB_AGENT_SIM_DB_FILE_SERVER_TOKEN=self._sim_db_file_token,
                SIREPO_PKCLI_JOB_AGENT_SIM_DB_FILE_SERVER_URI=job.supervisor_file_uri(
                    self.cfg.supervisor_uri,
                    job.SIM_DB_FILE_URI,
                    self.uid,
                ),
                SIREPO_PKCLI_JOB_AGENT_SUPERVISOR_URI=self.cfg.supervisor_uri.replace(
                    # TODO(robnagler) figure out why we need ws (wss, implicit)
                    "http",
                    "ws",
                    1,
                )
                + job.AGENT_URI,
            ),
            uid=self.uid,
        )

    def _agent_is_idle(self):
        return not self._prepared_sends and not self._websocket_ready_timeout

    async def _agent_ready(self, op):
        if self._websocket_ready.is_set():
            return True
        await self._agent_start(op)
        if op.is_destroyed:
            pkdlog("after agent_start op={} destroyed", op)
            return False
        pkdlog("{} {} await _websocket_ready", self, op)
        await self._websocket_ready.wait()
        pkdlog("{} {} websocket alive", self, op)
        if op.is_destroyed:
            pkdlog("after websocket_ready op={} destroyed", op)
            return False
        return True

    def _agent_receive(self, msg):
        def _default_unbound(msg):
            """Received msg unbound to op"""
            if j := msg.content.get("computeJid"):
                # SECURITY: assert agent can access to this uid
                if job.split_jid(j).uid == self.uid:
                    job_supervisor.agent_receive(msg.content)
                else:
                    pkdlog(
                        "{} jid={} not for this uid={}; msg={}", self, j, self.uid, msg
                    )
            else:
                pkdlog(
                    "{} missing computeJid, ignoring protocol error; msg={}", self, msg
                )

        def _error(content):
            if "error" in content:
                pkdlog("{} agent error msg={}", self, c)
                return "internal error in job_agent"
            pkdlog("{} no 'reply' in msg={}", self, c)
            return "invalid message from job_agent"

        def _log(content, op_id):
            if (
                "opName" not in content
                or content.opName == job.OP_ERROR
                or ("reply" in content and content.reply.get("state") == job.ERROR)
            ):
                # Log all errors, even without op_id
                pkdlog("{} error msg={}", self, content)
            else:
                pkdlog("{} opName={} o={:.4}", self, content.opName, op_id)

        def _reply(content, op_id):
            if "reply" not in content:
                # A protocol error but pass the state on
                content.reply = PKDict(state=job.ERROR, error=_error(content))
            if op_id in self._prepared_sends:
                # SECURITY: only ops known to this driver can be replied to
                self._prepared_sends[i].reply_put(content.reply)
            else:
                pkdlog(
                    "{} op not in prepared_sends opName={} o={:.4} content={}",
                    self,
                    content.opName,
                    op_id,
                    content,
                )

        c = msg.content
        i = c.get("opId")
        _log(c, i)
        if i:
            _reply(c, i)
        else:
            getattr(self, "_agent_receive_" + c.opName, _default_unbound)(msg)

    def _agent_receive_alive(self, msg):
        """Receive an ALIVE message from our agent

        Save the websocket and register self with the websocket
        """

        def _ignore():
            if self._websocket != msg.handler:
                pkdlog("{} reconnected to new websocket, closing old", self)
                self._websocket_close()
                return False
            if self._websocket_ready.is_set():
                # extra alive message is fine
                return True
            # TODO(robnagler) does this happen?
            pkdlog("{} websocket already set but not ready", self)
            return False

        self._websocket_ready_timeout_cancel()
        if self._websocket and _ignore():
            return
        self._websocket = msg.handler
        self._websocket_ready.set()
        self._websocket.sr_driver_set(self)
        self._start_idle_timeout()

    def _agent_receive_job_cmd_stderr(self, msg):
        """Log stderr from job_cmd"""
        pkdlog("{} stderr from job_cmd msg={}", self, msg.get("content"))

    async def _agent_start(self, op):
        if self._websocket_ready_timeout:
            # agent is already starting
            return
        try:
            async with self._agent_life_change_lock:
                if self.agent_is_ready_or_starting():
                    return
                pkdlog("{} {} await=_do_agent_start", self, op)
                # All awaits must be after this. If a call hangs the timeout
                # handler will cancel this task
                self._websocket_ready_timeout = (
                    tornado.ioloop.IOLoop.current().call_later(
                        self._agent_start_delay(op),
                        self._websocket_ready_timeout_handler,
                    )
                )
                await self._do_agent_start(op)
        except Exception as e:
            pkdlog("{} error={} stack={}", self, e, pkdexc())
            self._start_free_resources(caller="_agent_start")
            raise

    def _agent_start_delay(self, op):
        t = self.cfg.agent_starting_secs
        if not pkconfig.channel_in_internal_test():
            return t
        x = op.pkunchecked_nested_get("msg.data.models.dog.favoriteTreat")
        if not x:
            return t
        x = re.search(r"agent_start_delay=(\d+)", x)
        if not x:
            return t
        op._agent_start_delay = int(x.group(1))
        pkdlog("op={} agent_start_delay={}", op, self._agent_start_delay)
        return t + op._agent_start_delay

    def __str__(self):
        return f"{type(self).__name__}({self._agent_id:.4}, {self.uid:.4}, ops={list(self._prepared_sends.values())})"

    async def _slots_ready(self, op):
        """Allocate all required slots for op

        Slot allocation may require yielding so `_agent_ready` needs
        to be called if `HAD_TO_AWAIT` is true.

        All slots are allocated and only freed when the op is
        destroyed. We don't need to recheck the slots, because
        job_supervisor.destroy_op frees the slots. `_agent_ready` is state held
        outside this op so it needs to be rechecked when
        `HAD_TO_AWAIT` is returned from this method.

        If `OP_IS_DESTROYED` is encountered, exit immediately with that result.

        Return:
            job_supervisor.SlotAllocStatus: whether coroutine had to yield or op is destroyed
        """

        async def _alloc_check(alloc, msg):
            """Possibly call `alloc` and check `res`"""
            nonlocal res
            if res == job_supervisor.SlotAllocStatus.OP_IS_DESTROYED:
                pkdlog("op={} is destroyed", op)
                return res
            r = await alloc(msg)
            if r != job_supervisor.SlotAllocStatus.DID_NOT_AWAIT:
                res = r
            return res

        n = op.op_name
        res = job_supervisor.SlotAllocStatus.DID_NOT_AWAIT
        if n in job.OPS_WITHOUT_SLOTS:
            return res
        await _alloc_check(
            op.op_slot.alloc, "Waiting for another sim op to complete await=op_slot"
        )
        await _alloc_check(
            op.run_dir_slot.alloc,
            "Waiting for access to sim state await=run_dir_slot",
        )
        if n not in job.CPU_SLOT_OPS:
            return res
        # once job-op relative resources are acquired, ask for global resources
        # so we only acquire on global resources, once we know we are ready to go.
        return await _alloc_check(
            op.cpu_slot.alloc,
            "Waiting for CPU resources await=cpu_slot",
        )

    def _start_free_resources(self, caller):
        pkdlog("{} caller={}", self, caller)
        tornado.ioloop.IOLoop.current().add_callback(self.free_resources, caller=caller)

    def _start_idle_timeout(self):
        async def _kill_if_idle():
            try:
                self._idle_timer = None
                if self._agent_is_idle():
                    pkdlog("{}", self)
                    self._start_free_resources(caller="_kill_if_idle")
                else:
                    self._start_idle_timeout()
            except Exception as e:
                pkdlog("{} error={} stack={}", self, e, pkdexc())

        if not self._idle_timer:
            self._idle_timer = tornado.ioloop.IOLoop.current().call_later(
                _cfg.idle_check_secs,
                _kill_if_idle,
            )


def init_module(**imports):
    global _cfg, _CLASSES, _DEFAULT_CLASS

    if _cfg:
        return _cfg
    # import sirepo.job_supervisor
    sirepo.util.setattr_imports(imports)
    _cfg = pkconfig.init(
        modules=((_DEFAULT_MODULE,), set, "available job driver modules"),
        idle_check_secs=(
            1800,
            pkconfig.parse_seconds,
            "how many seconds to wait between checks",
        ),
    )
    _CLASSES = PKDict()
    p = pkinspect.this_module().__name__
    for n in _cfg.modules:
        m = importlib.import_module(pkinspect.module_name_join((p, n)))
        _CLASSES[n] = m.CLASS.init_class(job_supervisor)
    _DEFAULT_CLASS = _CLASSES.get("docker") or _CLASSES.get(_DEFAULT_MODULE)
    pkdlog("modules={}", sorted(_CLASSES.keys()))
    return _cfg


async def terminate():
    await DriverBase.terminate()
