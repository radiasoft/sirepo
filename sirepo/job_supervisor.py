"""Manage jobs and `job_agent` operations.

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern import pkconfig
from pykern import pkio
from pykern import pkjson
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdc, pkdformat, pkdlog, pkdexc
from sirepo import job
import aiofiles.os
import asyncio
import contextlib
import copy
import enum
import pykern.pkio
import pykern.pkjson
import re
import sirepo.const
import sirepo.global_resources
import sirepo.quest
import sirepo.simulation_db
import sirepo.srdb
import sirepo.srtime
import sirepo.tornado
import sirepo.util
import tornado.ioloop

#: where supervisor state is persisted to disk
_DB_DIR = None

_NEXT_REQUEST_SECONDS = None

_HISTORY_FIELDS = frozenset(
    (
        "alert",
        "canceledAfterSecs",
        "computeJobQueued",
        "computeJobSerial",
        "computeJobStart",
        "computeModel",
        "driverDetails",
        "error",
        "internalError",
        "isParallel",
        "isPremiumUser",
        "jobRunMode",
        "jobStatusMessage",
        "lastUpdateTime",
        "status",
    )
)

_PARALLEL_STATUS_FIELDS = frozenset(
    (
        "computeJobHash",
        "computeJobStart",
        "elapsedTime",
        "frameCount",
        "lastUpdateTime",
        "percentComplete",
        # TODO(robnagler) probably should be better labeled: what queue?
        "queueState",
    )
)

_RUN_STATUS_FIELDS = (
    "computeJid",
    "computeJobSerial",
    "computeModel",
    "isParallel",
    "jobRunMode",
    "simulationId",
    "simulationType",
    "uid",
)

_cfg = None

#: POSIT: same as sirepo.reply
_REPLY_SR_EXCEPTION_STATE = "srException"
_REPLY_ERROR_STATE = "error"
_REPLY_STATE = "state"


class InvalidRequest(Exception):
    pass


class SlotAllocStatus(enum.Enum):
    DID_NOT_AWAIT = 1
    HAD_TO_AWAIT = 2
    OP_IS_DESTROYED = 3


class ServerReq(PKDict):
    def pkdebug_str(self):
        if c := self.get("content"):
            return pkdformat("ServerReq({}, {})", c.get("api"), c.get("computeJid"))
        return "ServerReq(<no content>)"

    async def receive(self):
        s = self.content.pkdel("serverSecret")
        # no longer contains secret so ok to log
        if not s:
            pkdlog("no secret in message content={}", self.content)
            raise InvalidRequest()
        if s != sirepo.job.cfg().server_secret:
            pkdlog("server_secret did not match content={}", self.content)
            raise InvalidRequest()
        return await _Supervisor.receive(self)


class SlotProxy(PKDict):
    def __init__(self, **kwargs):
        super().__init__(_value=None, **kwargs)

    async def alloc(self, situation):
        if self._value is not None:
            return SlotAllocStatus.DID_NOT_AWAIT
        try:
            self._value = self._q.get_nowait()
            return SlotAllocStatus.DID_NOT_AWAIT
        except tornado.queues.QueueEmpty:
            pkdlog("{} situation={}", self._op, situation)
            with self._op.set_job_situation(situation):
                self._value = await self._q.get()
                if self._op.is_destroyed:
                    self.free()
                    return SlotAllocStatus.OP_IS_DESTROYED
            return SlotAllocStatus.HAD_TO_AWAIT

    def free(self):
        if self._value is None:
            return
        self._q.task_done()
        self._q.put_nowait(self._value)
        self._value = None


class SlotQueue(sirepo.tornado.Queue):
    def __init__(self, maxsize=1):
        super().__init__(maxsize=maxsize)
        for i in range(1, maxsize + 1):
            self.put_nowait(i)

    def sr_slot_proxy(self, op):
        return SlotProxy(_op=op, _q=self)


def init_module(**imports):
    global _cfg, _DB_DIR, _NEXT_REQUEST_SECONDS

    if _cfg:
        return
    # import sirepo.job_driver
    sirepo.util.setattr_imports(imports)
    _cfg = pkconfig.init(
        job_cache_secs=(300, int, "when to re-read job state from disk"),
        max_secs=dict(
            analysis=(
                144,
                pkconfig.parse_seconds,
                "maximum run-time for analysis job",
            ),
            io=(
                144,
                pkconfig.parse_seconds,
                "maximum run-time for io job",
            ),
            parallel=(
                3600,
                pkconfig.parse_seconds,
                "maximum run-time for parallel job (except sbatch)",
            ),
            parallel_premium=(
                3600 * 2,
                pkconfig.parse_seconds,
                "maximum run-time for parallel job for premium user (except sbatch)",
            ),
            sequential=(
                360,
                pkconfig.parse_seconds,
                "maximum run-time for sequential job",
            ),
        ),
        purge_check_interval=(
            None,
            pkconfig.parse_seconds,
            "time interval to clean up simulation runs of non-premium users, value of 0 means no checks are performed",
        ),
        purge_non_premium_after_secs=pkconfig.ReplacedBy(
            "sirepo.job_supervisor.run_dir_lifetime"
        ),
        purge_non_premium_task_secs=pkconfig.ReplacedBy(
            "sirepo.job_supervisor.purge_check_interval"
        ),
        run_dir_lifetime=(
            "1d",
            pkconfig.parse_seconds,
            "expiration period for purging non-premium users simulation run output",
        ),
        sbatch_poll_secs=(15, int, "how often to poll squeue and parallel status"),
    )
    _DB_DIR = sirepo.srdb.supervisor_dir()
    pykern.pkio.mkdir_parent(_DB_DIR)
    _NEXT_REQUEST_SECONDS = PKDict(
        {
            job.PARALLEL: 2,
            job.SBATCH: _cfg.sbatch_poll_secs,
            job.SEQUENTIAL: 1,
        }
    )
    _call_later(0, _ComputeJob.purge_non_premium)


def agent_receive(msg):
    """job_agent sent an async update

    Args:
        msg (str): msg content
    """
    _ComputeJob.agent_receive(msg)


async def terminate():
    await job_driver.terminate()


class _Supervisor(PKDict):
    def destroy_op(self, op):
        pass

    async def op_send_timeout(self, op):
        pass

    @classmethod
    async def receive(cls, req):
        if req.content.api != "api_runStatus":
            pkdlog("{}", req)
        try:
            with _Supervisor._process_request(req) as s:
                return await getattr(
                    s,
                    "_receive_" + req.content.api,
                )(req)
        except Exception as e:
            pkdlog("{} error={} stack={}", req, e, pkdexc())
            if isinstance(e, sirepo.util.ReplyExc):
                return _exception_reply(e)
            raise

    def pkdebug_str(self):
        c = self.pkunchecked_nested_get("req.content") or self
        return pkdformat(
            "_Supervisor(api={} uid={})",
            c.get("api"),
            c.get("uid"),
        )

    async def _cancel_op_or_job(self, timed_out_op=None, is_run_cancel=None):
        def _create_op(msg):
            # _create_op does too much and expects a request
            return _Op(
                _supervisor=_Supervisor(),
                api="cancel_or_timeout",
                driver=to_cancel.driver,
                is_destroyed=False,
                kind=to_cancel.kind,
                max_run_secs=None,
                msg=msg,
                op_name=job.OP_CANCEL,
                uid=self.db.uid,
            )

        def _eval_args_and_destroy_op():
            rv = PKDict()
            d = PKDict(status=job.CANCELED, queuedState=None)
            if timed_out_op:
                if timed_out_op.is_destroyed:
                    raise AssertionError(
                        "already destroyed timed_out_op={}", timed_out_op
                    )
                rv.opId = timed_out_op.op_id
                if timed_out_op.op_name == job.OP_RUN:
                    d.canceledAfterSecs = timed_out_op.max_run_secs
                    rv.jid = self.db.computeJid
                timed_out_op.destroy()
            elif is_run_cancel:
                if timed_out_op:
                    raise AssertionError("too many args")
                rv.jid = self.db.computeJid
            else:
                raise AssertionError("too few args")
            self.__db_status_update(**d)
            pkdlog("{} cancel args={}", self, rv)
            return rv

        c = None
        internal_error = None
        m = _eval_args_and_destroy_op()
        try:
            c = _create_op(m)
            if not await c.prepare_send() or c.is_destroyed:
                pkdlog("{} prepare_send failed op={}", self, c)
                return
            c.send()
            # state of "c" is irrelevant here, cancel always "succeeds".
            # no need to check return, but need to get the reply.
            await c.reply_get()
        except Exception as e:
            internal_error = f"_cancel_op_or_job exception={e}"
            pkdlog("exception={} stack={}", e, pkdexc())
        finally:
            if c:
                c.destroy(internal_error=internal_error)

    def _create_op(self, op_name, req, kind, job_run_mode, **msg_kwargs):
        return _Op(
            _supervisor=self,
            is_destroyed=False,
            kind=kind,
            msg=copy.deepcopy(req.content)
            .pksetdefault(jobRunMode=job_run_mode)
            .pkupdate(**msg_kwargs),
            op_name=op_name,
        )

    def _get_running_pending_jobs(self, uid=None):
        def _filter_jobs(job):
            if uid and job.db.uid != uid:
                return False
            return job._is_running_pending()

        def _get_header():
            h = PKDict(
                simulationType=PKDict(
                    title="App",
                    type="String",
                ),
                simulationId=PKDict(
                    title="Simulation id",
                    type="String",
                ),
                startTime=PKDict(
                    title="Start",
                    type="DateTime",
                ),
                lastUpdateTime=PKDict(
                    title="Last Update",
                    type="DateTime",
                ),
                elapsedTime=PKDict(
                    title="Elapsed",
                    type="Time",
                ),
                statusMessage=PKDict(
                    title="Status",
                    type="String",
                ),
            )
            if uid:
                h.name = PKDict(
                    title="Name",
                    type="String",
                )
            else:
                h.uid = PKDict(
                    title="User id",
                    type="String",
                )
                h.displayName = PKDict(
                    title="Display name",
                    type="String",
                )
                h.queuedTime = PKDict(
                    title="Queued",
                    type="Time",
                )
                h.driverDetails = PKDict(
                    title="Driver details",
                    type="String",
                )
                h.isPremiumUser = PKDict(
                    title="Premium user",
                    type="String",
                )
            return h

        def _get_jobs():
            def _get_queued_time(db):
                m = (
                    i.db.computeJobStart
                    if i.db.status == job.RUNNING
                    else sirepo.srtime.utc_now_as_int()
                )
                return m - db.computeJobQueued

            r = []
            with sirepo.quest.start() as qcall:
                for i in filter(_filter_jobs, _ComputeJob.instances.values()):
                    d = PKDict(
                        simulationType=i.db.simulationType,
                        simulationId=i.db.simulationId,
                        startTime=i.db.computeJobStart,
                        lastUpdateTime=i.db.lastUpdateTime,
                        elapsedTime=i.elapsed_time(),
                        statusMessage=i.db.get("jobStatusMessage", ""),
                        computeModel=sirepo.job.split_jid(
                            i.db.computeJid
                        ).compute_model,
                    )
                    if uid:
                        d.simName = i.db.simName
                    else:
                        d.uid = i.db.uid
                        d.displayName = (
                            qcall.auth_db.model("UserRegistration")
                            .search_by(uid=i.db.uid)
                            .display_name
                            or "n/a"
                        )
                        d.queuedTime = _get_queued_time(i.db)
                        d.driverDetails = " | ".join(
                            sorted(i.db.driverDetails.values())
                        )
                        d.isPremiumUser = i.db.isPremiumUser
                    r.append(d)
            return r

        return PKDict(header=_get_header(), jobs=_get_jobs())

    @classmethod
    @contextlib.contextmanager
    def _process_request(cls, req):
        if "computeJid" not in req.content:
            yield _Supervisor()
        else:
            with _ComputeJob.process_request(req) as rv:
                yield rv

    async def _receive_api_admJobs(self, req):
        return self._get_running_pending_jobs()

    async def _receive_api_beginSession(self, req):
        c = None
        try:
            c = self._create_op(job.OP_BEGIN_SESSION, req, job.SEQUENTIAL, "sequential")
            # This "if" documents the prepare_send protocol
            if not await c.prepare_send():
                # c is destroyed, do nothing
                pass
        finally:
            if c:
                c.destroy()
        # Always successful return, since spa_session ignores the reply
        return PKDict()

    async def _receive_api_globalResources(self, req):
        return sirepo.global_resources.for_simulation(
            req.content.data.simulationType,
            req.content.data.simulationId,
            uid=req.content.uid,
        )

    async def _receive_api_ownJobs(self, req):
        return self._get_running_pending_jobs(uid=req.content.uid)


class _ComputeJob(_Supervisor):
    instances = PKDict()
    _purged_jids_cache = set()

    def __init__(self, req):
        super().__init__(
            _active_req_count=0,
            ops=[],
            run_dir_slot_q=SlotQueue(),
            _run_status_active=False,
        )
        # At start we don't know anything about the run_dir so assume ready
        if d := self.__db_load(req.content.computeJid):
            self.db = d
        else:
            self.__db_init(req)
            self.__db_status_update()
        self.cache_timeout_set()

    @classmethod
    def agent_receive(cls, msg):
        if (j := msg.get("computeJid")) and (self := cls.instances.get(j)):
            if msg.opName in (job.OP_ERROR, job.OP_RUN_STATUS_UPDATE):
                self._process_run_status_update(msg)
            else:
                pkdlog("unhandled opName={} msg={} {}", msg.opName, msg, self)
        else:
            # This should not happen unless the job is purged
            pkdlog("inactive job jid={} msg={}", j, msg)

    def cache_timeout(self):
        if self._active_req_count > 0 or self.ops:
            self.cache_timeout_set()
        else:
            # No ops or reqs so nothing to destroy
            del self.instances[self.db.computeJid]

    def cache_timeout_set(self):
        self.timer = _call_later(_cfg.job_cache_secs, self.cache_timeout)

    def destroy_op(self, op):
        if op in self.ops:
            self.ops.remove(op)
        super().destroy_op(op)

    def elapsed_time(self):
        if not self.db.computeJobStart:
            return 0
        return (
            sirepo.srtime.utc_now_as_int()
            if self._is_running_pending()
            else int(self.db.dbUpdateTime)
        ) - self.db.computeJobStart

    async def op_send_timeout(self, op):
        if op.is_destroyed:
            return
        await self._cancel_op_or_job(timed_out_op=op)

    def pkdebug_str(self):
        d = self.get("db")
        if not d:
            return "_ComputeJob()"
        return pkdformat(
            "_ComputeJob({} u={} {} {})",
            d.get("computeJid"),
            d.get("uid"),
            d.get("status"),
            self.ops,
        )

    @classmethod
    @contextlib.contextmanager
    def process_request(cls, req):
        def _authenticate(self):
            # SECURITY: must only return instances for authorized user
            if req.content.uid != self.db.uid:
                pkdlog(
                    "req.content.uid={} is not same as db.uid={} for jid={}",
                    req.content.uid,
                    self.db.uid,
                    req.content.computeJid,
                )
                raise InvalidRequest()
            return self

        def _get_or_create():
            if self := cls.instances.get(req.content.computeJid):
                return _authenticate(self)
            return cls._create(req)

        self = None
        try:
            self = _get_or_create()
            self._active_req_count += 1
            yield self
        finally:
            if self:
                self._active_req_count -= 1

    @classmethod
    async def purge_non_premium(cls):
        def _purge_job(jid, too_old, qcall):
            if jid in _ComputeJob.instances:
                pkdlog(
                    "jid=[} in _ComputeJob.instances; should not happen, ignoring", jid
                )
                return
            if (d := cls.__db_load(jid)) is None:
                return
            if d.lastUpdateTime > too_old:
                return
            cls._purged_jids_cache.add(jid)
            if d.status == job.JOB_RUN_PURGED or not sirepo.util.is_sim_type(
                d.simulationType
            ):
                return
            try:
                # TODO(robnagler) need async version of unchecked_remove
                sirepo.simulation_db.simulation_run_dir(d, remove_dir=True, qcall=qcall)
            except sirepo.util.UserDirNotFound:
                pkdlog(
                    "not found user_path={} not recreating jid={}",
                    sirepo.simulation_db.user_path(check=none, qcall=qcall),
                    jid,
                )
                return
            n = cls.__db_init_new(d, d)
            n.status = job.JOB_RUN_PURGED
            cls.__db_write_file(n)
            pkdlog("jid={}", jid)

        async def _uids_to_jids(too_old, qcall):
            paid_users = qcall.auth_db.model("UserRole").uids_of_paid_users()
            is_json = re.compile(rf"^(\w.+){sirepo.const.JSON_SUFFIX}$")
            rv = PKDict()
            for e in await aiofiles.os.scandir(_DB_DIR):
                m = is_json.search(e.name)
                if not m:
                    continue
                j = m.group(1)
                u = sirepo.job.split_jid(jid=j).uid
                if (
                    u not in paid_users
                    and e.stat(follow_symlinks=False).st_mtime <= too_old
                    and j not in cls._purged_jids_cache
                ):
                    if u in rv:
                        rv[u].append(j)
                    else:
                        rv[u] = [j]
            return rv

        if not _cfg.purge_check_interval:
            return
        pkdlog("start")
        u = None
        j = None
        try:
            too_old = sirepo.srtime.utc_now_as_int() - _cfg.run_dir_lifetime
            with sirepo.quest.start() as qcall:
                for u, jids in (await _uids_to_jids(too_old, qcall)).items():
                    with qcall.auth.logged_in_user_set(u):
                        for j in jids:
                            _purge_job(jid=j, too_old=too_old, qcall=qcall)
                    await sirepo.util.yield_to_event_loop()
        except Exception as e:
            pkdlog("u={} j={} error={} stack={}", u, j, e, pkdexc())
        finally:
            _call_later(_cfg.purge_check_interval, cls.purge_non_premium)
        pkdlog("done")

    def set_situation(self, op, situation, exception=None):
        if op.op_name != job.OP_RUN:
            return
        s = self.db.jobStatusMessage
        p = "Exception: "
        if situation is not None:
            # POSIT: no other situation begins with exception
            assert not s or not s.startswith(
                p
            ), f'Trying to overwrite existing jobStatusMessage="{s}" with situation="{situation}"'
        if exception is not None:
            if not str(exception):
                exception = repr(exception)
            situation = f"{p}{exception}, while {s}"
        self.__db_update(jobStatusMessage=situation)

    @classmethod
    def _create(cls, req):
        self = cls.instances[req.content.computeJid] = cls(req)
        # sbatch status will be checked by first runStatus
        if self._is_running_pending() and self.db.jobRunMode != job.SBATCH:
            # TODO(robnagler) when we reconnect with docker
            # containers at startup, we'll need to change this.
            # See https://github.com/radiasoft/sirepo/issues/6916
            pkdlog(
                "canceling after reload jid={} {}",
                self.db.computeJid,
                req.content.api,
            )
            self.__db_status_update(status=job.CANCELED)
        return self

    def _create_op(self, op_name, req, **msg_kwargs):
        req.simulationType = self.db.simulationType
        # run mode can change between runs so use req.content.jobRunMode
        # not self.db.jobRunMode
        r = req.content.get("jobRunMode", self.db.jobRunMode)
        if r not in sirepo.simulation_db.JOB_RUN_MODE_MAP:
            # happens only when config changes, and only when sbatch is missing
            raise sirepo.util.NotFound("invalid jobRunMode={} req={}", r, req)
        msg_kwargs.setdefault(
            "kind",
            (
                job.PARALLEL
                if self.db.isParallel and op_name != job.OP_ANALYSIS
                else job.SEQUENTIAL
            ),
        )
        o = (
            super()
            ._create_op(op_name, req, job_run_mode=r, **msg_kwargs)
            .pkupdate(task=asyncio.current_task())
        )
        self.ops.append(o)
        return o

    @classmethod
    def __db_file(cls, computeJid):
        return _DB_DIR.join(
            sirepo.simulation_db.assert_sim_db_basename(computeJid)
            + sirepo.const.JSON_SUFFIX,
        )

    def __db_init(self, req, prev_db=None):
        self.db = self.__db_init_new(req.content, prev_db)
        return self.db

    @classmethod
    def __db_init_new(cls, data, prev_db=None):
        db = PKDict(
            alert=None,
            queueState="queued",
            canceledAfterSecs=None,
            computeJid=data.computeJid,
            computeJobHash=data.get("computeJobHash"),
            computeJobQueued=0,
            computeJobSerial=0,
            computeJobStart=0,
            computeModel=data.computeModel,
            # Need high resolution because used as a transaction timestamp
            dbUpdateTime=sirepo.srtime.utc_now_as_float(),
            driverDetails=PKDict(),
            error=None,
            history=cls.__db_init_history(prev_db),
            isParallel=data.isParallel,
            isPremiumUser=data.get("isPremiumUser"),
            jobStatusMessage=None,
            lastUpdateTime=0,
            simName=None,
            simulationId=data.simulationId,
            simulationType=data.simulationType,
            status=job.MISSING,
            uid=data.uid,
        )
        r = data.get("jobRunMode")
        if not r:
            assert (
                data.api != "api_runSimulation"
            ), "api_runSimulation must have a jobRunMode content={}".format(data)
            # __db_init() will be called when runDirNotFound.
            # The api_* that initiated the request may not have
            # a jobRunMode (ex api_downloadDataFile). In that
            # case use the existing jobRunMode because the
            # request doesn't care about the jobRunMode
            r = prev_db.jobRunMode
        db.pkupdate(
            jobRunMode=r,
            nextRequestSeconds=_NEXT_REQUEST_SECONDS[r],
        )
        if db.isParallel:
            db.parallelStatus = PKDict(
                ((k, 0) for k in _PARALLEL_STATUS_FIELDS),
            )
        return db

    @classmethod
    def __db_init_history(cls, prev_db):
        if prev_db is None:
            return []
        return prev_db.history + [
            PKDict(((k, v) for k, v in prev_db.items() if k in _HISTORY_FIELDS)),
        ]

    @classmethod
    def __db_load(cls, compute_jid):
        def _fixup(old):
            old.pksetdefault(
                # Simple cases of missing defaults
                computeModel=lambda: sirepo.job.split_jid(compute_jid).compute_model,
                queueState=None,
            )
            if "dbUpdateTime" not in values:
                values.dbUpdateTime = float(p.mtime())
            elif isinstance(old.dbUpdateTime, int):
                # make type compatible
                old.dbUpdateTime = float(old.dbUpdateTime)
            if "cancelledAfterSecs" in old:
                # correct spelling
                old.canceledAfterSecs = old.pkdel("cancelledAfterSecs", default=None)
                for h in old.history:
                    h.canceledAfterSecs = old.pkdel("cancelledAfterSecs", default=None)
            return old

        p = cls.__db_file(compute_jid)
        try:
            d = p.read_binary()
        except Exception as e:
            if pykern.pkio.exception_is_not_found(e):
                pkdlog("disappeared path={}", p)
                return None
            raise
        d = pkjson.load_any(d)
        for k in [
            "alert",
            "canceledAfterSecs",
            "isPremiumUser",
            "jobStatusMessage",
            "internalError",
        ]:
            d.setdefault(k, None)
            for h in d.history:
                h.setdefault(k, None)
        return _fixup(d)

    def __db_status_update(self, **kwargs):
        if not (
            "status" in kwargs
            and self._is_running_pending(kwargs["status"])
            and self._is_running_pending
        ):
            # Need to ask the agent for status
            self._run_status_active = False
        self.__db_update(**kwargs)

    def __db_update(self, **kwargs):
        self.db.pkupdate(**kwargs)
        self.__db_write_file(self.db)

    @classmethod
    def __db_write_file(cls, db):
        kwargs.dbUpdateTime = sirepo.srtime.utc_now_as_float()
        sirepo.util.json_dump(db, path=cls.__db_file(db.computeJid))

    def __db_copy_to_dest(self, dest, fields):
        for f in fields:
            dest[f] = self.db[f]
        return dest

    def _is_running_pending(self, status=None):
        return (status or self.db.status) in (job.RUNNING, job.PENDING)

    def _init_db_missing_response(self, req):
        self.__db_init(req, prev_db=self.db)
        self.__db_status_update()
        if self.db.status != job.MISSING:
            raise AssertionError(f"expecting missing status={self.db.status}")
        return PKDict(state=self.db.status)

    def _process_run_status_update(self, reply):
        """Process msg from agent about job"""
        if self.db.computeJobSerial != reply.computeJobSerial:
            pkdlog(
                "{} db.computeJobSerial={} does not match reply={}, ignoring",
                self,
                self.db.computeJobSerial,
                reply.computeJobSerial,
            )
            return
        d = PKDict(status=reply.state, alert=reply.get("alert"))
        if self.db.isParallel:
            # TODO(robnagler) document: tells the UI it is no longer queued in slurm
            d.queueState = None
        if self.db.status == job.ERROR:
            d.error = reply.get("error", "<unknown error>")
        if "computeJobStart" in reply:
            d.computeJobStart = reply.computeJobStart
        if "parallelStatus" in reply:
            # TODO(robnagler) Need to pass this, but may be nested
            self.db.parallelStatus.update(reply.parallelStatus)
            d.lastUpdateTime = reply.parallelStatus.lastUpdateTime
        else:
            # agent doesn't always send the time
            d.lastUpdateTime = (
                reply.get("lastUpdateTime") or sirepo.srtime.utc_now_as_int()
            )
        # TODO(robnagler) will need final frame count. Not sent?
        self.__db_status_update(d)

    def _raise_if_purged_or_missing(self, req):
        if self.db.status in (job.MISSING, job.JOB_RUN_PURGED):
            raise sirepo.util.NotFound("purged or missing {}", req)

    async def _receive_api_analysisJob(self, req):
        return await self._send_op_analysis(req, "analysis_job")

    async def _receive_api_downloadDataFile(self, req):
        return await self._receive_api_downloadRunFile(req)

    async def _receive_api_downloadRunFile(self, req):
        self._raise_if_purged_or_missing(req)
        return await self._send_with_single_reply(
            job.OP_IO,
            req,
            jobCmd=job.CMD_DOWNLOAD_RUN_FILE,
        )

    async def _receive_api_runCancel(self, req, timed_out_op=None):
        """Cancel a run

        Args:
            req (ServerReq): The cancel request
            timed_out_op (_Op, Optional): the op that was timed out, which needs to be canceled
        Returns:
            PKDict: Message with state=canceled
        """

        if not self._req_is_valid(req) or not self._is_running_pending():
            pkdlog("{} ignoring cancel, not running req_is_invalid", self)
            # job is not relevant, but let the user know it isn't running
            return _canceled_reply()
        await self._cancel_op_or_job(is_run_cancel=True)
        return _canceled_reply()

    async def _receive_api_runSimulation(self, req, recursing=False):
        def _update_db():
            self.__db_init(req, prev_db=self.db)
            t = sirepo.srtime.utc_now_as_int()
            self.__db_status_update(
                computeJobQueued=t,
                computeJobSerial=t,
                computeModel=req.content.computeModel,
                # run mode can change between runs so we must update the db
                jobRunMode=req.content.jobRunMode,
                simName=req.content.data.models.simulation.name,
                status=job.PENDING,
            )
            self._purged_jids_cache.discard(
                self.__db_file(self.db.computeJid).purebasename
            )

        def _validate(force_run):
            if self._is_running_pending():
                if force_run or not self._req_is_valid(req):
                    return PKDict(
                        state=job.ERROR,
                        error="another browser is running the simulation",
                    )
                # Not _receive_api_runStatus, because runStatus should have been
                # called before this function is called.
                return self._status_reply(req)
            if (
                not force_run
                and self._req_is_valid(req)
                and self.db.status == job.COMPLETED
            ):
                # TODO(robnagler) simplify after https://github.com/radiasoft/sirepo/issues/7386

                # Valid, completed, sequential simulation
                # Read this first https://github.com/radiasoft/sirepo/issues/2007
                r = await self._receive_api_runStatus(req)
                if r.state == job.MISSING:
                    # happens when the run dir is deleted (ex purge_non_premium)
                    if recursing:
                        raise AssertionError(f"already called from self req={req}")
                    # Rerun the simulation, since there's no "button" in the UI for
                    # this case.
                    return await self._receive_api_runSimulation(req, recursing=True)
                return r
            return None

        if r := _validate(req.content.data.get("forceRun")):
            return r
        _update_db(self, sirepo.srtime.utc_now_as_int(), self.db)
        r = await self._send_with_single_reply(
            job.OP_RUN,
            req,
            jobCmd=job.CMD_COMPUTE,
            nextRequestSeconds=self.db.nextRequestSeconds,
        )
        if r.state != job.STATE_OK:
            return r
        return await self._receive_api_runStatus(req)

    async def _receive_api_runStatus(self, req):
        async def _ask_agent():
            self._run_status_active = True
            d = self.db.dbUpdateTime
            r = await self._send_with_reply(
                job.OP_RUN_STATUS,
                req=_req(),
            )
            if self.db.dbUpdateTime == d:
                # db has not been modified since request
                _update(r.reply)
            r.op.destroy()

        def _req():
            return PKDict(
                content=self.__db_copy_to_dest(PKDict, _RUN_STATUS_FIELDS).pkupdate(
                    # Note: overriden by drivers sometimes so not kept in db
                    runDir=req.content.runDir,
                    userDir=req.content.userDir,
                ),
                runStatusPollSeconds=self.db.nextRequestSeconds,
            )

        def _update_status(reply):
            # Can modify the db
            if r is None:
                # Unclear what the status is so just retry
                self._run_status_active = False
                return
            # unknown means driver is still querying service
            if reply.state == job.UNKNOWN:
                if e := reply.get("error"):
                    self._run_status_active = False
                    pkdlog("{} run_status error={}, ignoring", self, e)
                # else normal case of indeterminate state and run_status will continue
                return
            if reply.computeJobSerial != self.db.computeJobSerial:
                # TODO(robnagler) probably need to kill job if reply.status is running?
                self._run_status_active = False
                pkdlog(
                    "{} db.computeJobSerial={} does not match reply={}",
                    self,
                    self.db.computeJobSerial,
                    reply,
                )
                return
            # Reply only includes state at this point; OP_RUN_STATUS_UPDATE handles that
            self.__db_status_update(status=reply.state)

        if self._is_running_pending() and not self._run_status_active:
            await _ask_agent()
        r = self._status_reply(req)
        if self.db.isParallel or r.status != job.COMPLETED:
            return r
        r = await self._send_op_analysis(req, "sequential_result")
        # TODO(robnagler) do we need to check global state?
        if r.state == job.ERROR and "errorCode" not in r:
            # TODO(robnagler) this seems wrong. Should be explicit
            return self._init_db_missing_response(req)
        return r

    async def _receive_api_sbatchLoginStatus(self, req):
        return PKDict(ready=self._is_sbatch_login_ok(req))

    async def _receive_api_sbatchLogin(self, req):
        # Prevents unnecessary messages, but does not eliminate all
        if self._is_sbatch_login_ok(req):
            return job.sbatch_login_ok()
        return await self._send_with_single_reply(job.OP_SBATCH_LOGIN, req)

    async def _receive_api_simulationFrame(self, req):
        if not self._req_is_valid(req):
            raise sirepo.util.NotFound("invalid req={}", req)
        self._raise_if_purged_or_missing(req)
        return await self._send_op_analysis(req, "get_simulation_frame")

    async def _receive_api_statefulCompute(self, req):
        return await self._send_op_analysis(req, "stateful_compute")

    async def _receive_api_statelessCompute(self, req):
        return await self._send_op_analysis(req, "stateless_compute")

    def _is_sbatch_login_ok(self, req):
        o = self._create_op(job.OP_SBATCH_AGENT_READY, req)
        try:
            return o.assign_driver().agent_is_ready_or_starting()
        finally:
            o.destroy()

    def _req_is_valid(self, req):
        return self.db.computeJobHash == req.content.computeJobHash and (
            not req.content.computeJobSerial
            or self.db.computeJobSerial == req.content.computeJobSerial
        )

    async def _send_op_analysis(self, req, jobCmd):
        pkdlog(
            "{} api={} method={}",
            req,
            jobCmd,
            req.content.data.get("method"),
        )
        return await self._send_with_single_reply(job.OP_ANALYSIS, req, jobCmd=jobCmd)

    async def _send_with_reply(self, op_name, req, **kwargs):
        async def _send(op):
            if not await op.prepare_send() or op.is_destroyed:
                return None, False
            op.send()
            if (r := await op.reply_get()) is None:
                return None, False
            # POSIT: any api_* that could run into runDirNotFound
            # will call _send_with_single_reply() and this will
            # properly format the reply
            if r.get("runDirNotFound"):
                return self._init_db_missing_response(req), False
            return r, True

        o = None
        internal_error = None
        try:
            o = self._create_op(op_name, req, **kwargs)
            r, k = _send(o)
            rv = PKDict(reply=r, op=o)
            if k:
                o = None
            return rv
        except Exception as e:
            internal_error = f"_send_with_reply exception={e}"
            raise
        finally:
            if o:
                o.destroy(internal_error=internal_error)

    async def _send_with_single_reply(self, op_name, req, **kwargs):
        r = await self._send_with_reply(op_name, req, **kwargs)
        r.op.destroy()
        return _canceled_reply() if r.reply is None else r.reply

    def _status_reply(self, req):
        def _result(**kwargs):
            r = PKDict(
                state=self.db.status,
                # End users don't see float
                dbUpdateTime=int(self.db.dbUpdateTime),
            )
            if self.db.canceledAfterSecs is not None:
                r.canceledAfterSecs = self.db.canceledAfterSecs
            # TODO(robnagler) could always be set?
            if self.db.error:
                r.error = self.db.error
            if self.db.alert:
                r.alert = self.db.alert
            if self.db.isParallel:
                r.update(self.db.parallelStatus)
                self.__db_copy_to_dest(
                    # TODO(robnagler) why are these not included in all cases?
                    r,
                    (
                        "computeJobHash",
                        "computeJobSerial",
                        "computeModel",
                        "queueState",
                    ),
                )
                r.elapsedTime = self.elapsed_time()
            if self._is_running_pending():
                # TODO(robnagler) why are there two copies of nextRequestSeconds?
                self.__db_copy_to_dest(r, ("jobStatusMessage", "nextRequestSeconds"))
                r.nextRequest = self.__db_copy_to_dest(
                    PKDict(), _RUN_STATUS_FIELDS
                ).pkupdate(
                    # TODO(robnagler) is this value necessary?
                    report=req.content.analysisModel,
                )
            return r

        if self._req_is_valid():
            return _result()
        return PKDict(
            state=job.MISSING,
            reason=(
                "computeJobSerial-mismatch"
                if self.db.computeJobHash == req.content.computeJobHash
                else "computeJobHash-mismatch"
            ),
        )


class _Op(PKDict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.update(
            internal_error=None,
            op_id=sirepo.util.unique_key(),
            _reply_q=sirepo.tornado.Queue(),
        )
        if "run_dir_slot_q" in self._supervisor:
            self.run_dir_slot = self._supervisor.run_dir_slot_q.sr_slot_proxy(self)
        self.msg.update(opId=self.op_id, opName=self.op_name)
        pkdlog("{} runDir={}", self, self.msg.get("runDir"))

    def assign_driver(self):
        self.driver = job_driver.assign_instance_op(self)
        return self.driver

    def destroy(self, internal_error=None):
        """Idempotently destroy op

        Args:
            internal_error (str): saved for logging in `destroy_op` [default: None]
        """
        try:
            if self.is_destroyed:
                return
            self.is_destroyed = True
            if internal_error and not self.internal_error:
                self.internal_error = internal_error
            if x := self.pkdel("_reply_q"):
                x.put_nowait(None)
            for x in "cpu_slot", "op_slot", "run_dir_slot":
                if y := self.pkdel(x):
                    y.free()
            for x in ("timer",):
                if y := self.pkdel(x):
                    tornado.ioloop.IOLoop.current().remove_timeout(y)
            self._supervisor.destroy_op(self)
            if "driver" in self:
                self.driver.destroy_op(self)
        except Exception as e:
            pkdlog("ignore exception={} stack={}", e, pkdexc())

    def pkdebug_str(self):
        def _internal_error():
            if not self.get("internal_error"):
                return ""
            return ", internal_error={self.internal_error}"

        return pkdformat(
            "_Op({}{}, {:.4}{})",
            "DESTROYED, " if self.get("is_destroyed") else "",
            self.get("op_name"),
            self.get("op_id"),
            _internal_error(),
        )

    async def prepare_send(self):
        """Ensures resources are available for sending to agent
        To maintain consistency, do not modify global state before
        calling this method.

        Returns:
            bool: If False, op is destroyed, exit immediately
        """
        if "driver" not in self:
            self.assign_driver()
            pkdlog("assigned driver={} to op={}", self.driver, self)
            self.cpu_slot = self.driver.cpu_slot_q.sr_slot_proxy(self)
            if q := self.driver.op_slot_q.get(self.op_name):
                self.op_slot = q.sr_slot_proxy(self)
            self.max_run_secs = self._get_max_run_secs()
            if "dataFileKey" in self.msg:
                self.msg.dataFileUri = job.supervisor_file_uri(
                    self.driver.cfg.supervisor_uri,
                    job.DATA_FILE_URI,
                    self.msg.pop("dataFileKey"),
                )
        return await self.driver.prepare_send(self)

    async def reply_get(self):
        pkdlog("{} await _reply_q.get()", self)
        if (r := await self._reply_q.get()) is None:
            pkdlog("{} no reply", self)
            return None
        self._reply_q.task_done()
        return r

    def reply_put(self, reply_op_name, reply_content):
        self._reply_q.put_nowait(reply_content)

    def send(self):
        async def _timeout():
            pkdlog("{} max_run_secs={}", self, self.max_run_secs)
            await self._supervisor.op_send_timeout(self)

        if self.max_run_secs:
            self.timer = _call_later(self.max_run_secs, _timeout)
        self.driver.send(self)

    @contextlib.contextmanager
    def set_job_situation(self, situation):
        self._supervisor.set_situation(self, situation)
        try:
            yield
            self._supervisor.set_situation(self, None)
        except Exception as e:
            pkdlog("{} situation={} stack={}", self, situation, pkdexc())
            self._supervisor.set_situation(self, None, exception=e)
            raise

    def _get_max_run_secs(self):
        if self.driver.op_is_untimed(self):
            return 0
        if self.op_name in (
            sirepo.job.OP_ANALYSIS,
            sirepo.job.OP_IO,
        ):
            return _cfg.max_secs[self.op_name]
        if self.kind == job.PARALLEL and self.msg.get("isPremiumUser"):
            return _cfg.max_secs["parallel_premium"]
        return _cfg.max_secs[self.kind]

    def __hash__(self):
        return hash((self.op_id,))


def _call_later(*args, **kwargs):
    """Simplifies many calls. Probably should be create_task with a delay"""
    return tornado.ioloop.IOLoop.current().call_later(*args, **kwargs)


def _canceled_reply():
    return PKDict(state=job.CANCELED)


def _exception_reply(exc):
    if isinstance(exc, sirepo.util.SRException):
        return PKDict(
            {
                _REPLY_STATE: _REPLY_SR_EXCEPTION_STATE,
                _REPLY_SR_EXCEPTION_STATE: exc.sr_args,
            }
        )
    if isinstance(exc, sirepo.util.UserAlert):
        return PKDict(
            {
                _REPLY_STATE: _REPLY_ERROR_STATE,
                _REPLY_ERROR_STATE: exc.sr_args.error,
            }
        )
    raise AssertionError(f"Reply class={exc.__class__.__name__} unknown exc={exc}")
