"""Manage batch executions of template codes

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
        "queueState",
    )
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
    def copy_content(self):
        return copy.deepcopy(self.content)

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
    tornado.ioloop.IOLoop.current().add_callback(_ComputeJob.purge_non_premium)


async def terminate():
    await job_driver.terminate()


class _Supervisor(PKDict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._must_verify_status = False

    def destroy_op(self, op):
        pass

    @classmethod
    @contextlib.contextmanager
    def get_instance(cls, req):
        if "computeJid" not in req.content:
            yield _Supervisor()
        else:
            with _ComputeJob.get_instance(req) as rv:
                yield rv

    def pkdebug_str(self):
        c = self.pkunchecked_nested_get("req.content") or self
        return pkdformat(
            "_Supervisor(api={} uid={})",
            c.get("api"),
            c.get("uid"),
        )

    @classmethod
    async def receive(cls, req):
        if req.content.get("api") != "api_runStatus":
            pkdlog("{}", req)
        try:
            with _Supervisor.get_instance(req) as s:
                if s._must_verify_status and (r := await s._verify_status(req)):
                    return r
                # instance may need to be checked
                return await getattr(
                    s,
                    "_receive_" + req.content.api,
                )(req)
        except Exception as e:
            pkdlog("{} error={} stack={}", req, e, pkdexc())
            if isinstance(e, sirepo.util.ReplyExc):
                return _exception_reply(e)
            raise

    async def op_send_timeout(self, op):
        pass

    async def _cancel_op(self, to_cancel):
        def _create_op():
            # _create_op does too much and expects a request
            return _Op(
                _supervisor=_Supervisor(),
                api="cancel_or_timeout",
                driver=to_cancel.driver,
                is_destroyed=False,
                kind=to_cancel.kind,
                max_run_secs=None,
                msg=PKDict(opIdsToCancel=[to_cancel.op_id]),
                op_name=job.OP_CANCEL,
                uid=to_cancel.driver.uid,
            )

        c = None
        internal_error = None
        try:
            if to_cancel.is_destroyed:
                pkdlog("{} to_cancel={} destroyed", self, to_cancel)
                return
            c = _create_op()
            pkdlog("{} to_cancel={}", self, to_cancel)
            to_cancel.destroy()
            if not await c.prepare_send() or c.is_destroyed:
                pkdlog("{} prepare_send failed to_cancel={}", self, to_cancel)
                return
            c.send()
            # state of "c" is irrelevant here, cancel always "succeeds".
            # no need to check return, but need to get the reply.
            await c.reply_get()
        except Exception as e:
            internal_error = f"_cancel_op exception={e}"
            pkdlog("exception={} stack={}", e, pkdexc())
        finally:
            if c:
                c.destroy(internal_error=internal_error)

    def _create_op(self, op_name, req, kind, job_run_mode, **kwargs):
        return _Op(
            _supervisor=self,
            is_destroyed=False,
            kind=kind,
            msg=PKDict(req.copy_content())
            .pksetdefault(jobRunMode=job_run_mode)
            .pkupdate(**kwargs),
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
            run_op=None,
            run_dir_slot_q=SlotQueue(),
        )
        # At start we don't know anything about the run_dir so assume ready
        if d := self.__db_load(req.content.computeJid):
            self.db = d
        else:
            self.__db_init(req)
            self.__db_write()
        self.cache_timeout_set()

    def cache_timeout(self):
        if self._active_req_count > 0 or self.ops:
            self.cache_timeout_set()
        else:
            del self.instances[self.db.computeJid]

    def cache_timeout_set(self):
        self.timer = tornado.ioloop.IOLoop.current().call_later(
            _cfg.job_cache_secs,
            self.cache_timeout,
        )

    def destroy_op(self, op):
        if op in self.ops:
            self.ops.remove(op)
        if self.run_op == op:
            self.run_op = None
        super().destroy_op(op)

    def elapsed_time(self):
        if not self.db.computeJobStart:
            return 0
        return (
            sirepo.srtime.utc_now_as_int()
            if self._is_running_pending()
            else int(self.db.dbUpdateTime)
        ) - self.db.computeJobStart

    @classmethod
    @contextlib.contextmanager
    def get_instance(cls, req):
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

    async def op_send_timeout(self, op):
        if op.is_destroyed:
            return
        if self.run_op == op:
            self.__db_update(
                canceledAfterSecs=op.max_run_secs,
                status=job.CANCELED,
                queuedState=None,
            )
        await self._cancel_op(op)

    @classmethod
    async def purge_non_premium(cls):
        def _purge_job(jid, too_old, qcall):
            d = cls.__db_load(jid)
            if d is None:
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
            tornado.ioloop.IOLoop.current().call_later(
                _cfg.purge_check_interval,
                cls.purge_non_premium,
            )
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
        if self._is_running_pending():
            # Easiest place to have special case
            if self.db.jobRunMode == job.SBATCH:
                self._must_verify_status = True
            else:
                # TODO(robnagler) when we reconnect with docker
                # containers at startup, we'll need to change this.
                # See https://github.com/radiasoft/sirepo/issues/6916
                self.__db_update(status=job.CANCELED)
        return self

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
        v = None
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
            d.setdefault(k, v)
            for h in d.history:
                h.setdefault(k, v)
        d.pksetdefault(
            computeModel=lambda: sirepo.job.split_jid(compute_jid).compute_model,
            # No need for async, because upgrading old files
            dbUpdateTime=lambda: float(p.mtime()),
        )
        if isinstance(d.dbUpdateTime, int):
            # Fixup so type compatible
            d.dbUpdateTime = float(d.dbUpdateTime)
        if "cancelledAfterSecs" in d:
            # update spelling
            d.canceledAfterSecs = d.pkdel("cancelledAfterSecs", default=v)
            for h in d.history:
                h.canceledAfterSecs = d.pkdel("cancelledAfterSecs", default=v)
        return d

    def __db_update(self, **kwargs):
        self.db.pkupdate(**kwargs)
        return self.__db_write()

    def __db_write(self):
        self.db.dbUpdateTime = sirepo.srtime.utc_now_as_float()
        self.__db_write_file(self.db)
        return self

    @classmethod
    def __db_write_file(cls, db):
        sirepo.util.json_dump(db, path=cls.__db_file(db.computeJid))

    def _is_running_pending(self):
        return self.db.status in (job.RUNNING, job.PENDING)

    def _init_db_missing_response(self, req):
        self.__db_init(req, prev_db=self.db)
        self.__db_write()
        assert self.db.status == job.MISSING, "expecting missing status={}".format(
            self.db.status
        )
        return PKDict(state=self.db.status)

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
            jobCmd="download_run_file",
        )

    async def _receive_api_runCancel(self, req, timed_out_op=None):
        """Cancel a run

        Args:
            req (ServerReq): The cancel request
            timed_out_op (_Op, Optional): the op that was timed out, which needs to be canceled
        Returns:
            PKDict: Message with state=canceled
        """

        def _find_op():
            rv = [o for o in self.ops if o.op_name == job.OP_RUN]
            if not rv:
                return None
            if len(rv) > 1:
                raise AssertionError("too many OP_RUN ops={}", rv)
            return rv[0]

        if not self._req_is_valid(req) or not self._is_running_pending():
            pkdlog("{} ignoring cancel, not running req_is_invalid", self)
            # job is not relevant, but let the user know it isn't running
            return _canceled_reply()
        # No matter what happens the job is canceled at this point
        self.__db_update(status=job.CANCELED, queuedState=None)
        if not (o := _find_op()):
            # no run op so just pending
            return _canceled_reply()
        await self._cancel_op(o)
        return _canceled_reply()

    async def _receive_api_runSimulation(self, req, recursing=False):
        f = req.content.data.get("forceRun")
        if self._is_running_pending():
            if f or not self._req_is_valid(req):
                return PKDict(
                    state=job.ERROR,
                    error="another browser is running the simulation",
                )
            return self._status_reply(req)
        if not f and self._req_is_valid(req) and self.db.status == job.COMPLETED:
            # Valid, completed, transient simulation
            # Read this first https://github.com/radiasoft/sirepo/issues/2007
            r = await self._receive_api_runStatus(req)
            if r.state == job.MISSING:
                # happens when the run dir is deleted (ex purge_non_premium)
                if recursing:
                    raise AssertionError(f"already called from self req={req}")
                return await self._receive_api_runSimulation(req, recursing=True)
            return r
        if self.run_op:
            pkdlog("unexpected run_op={} so error on new req={}", self.run_op, req)
            return PKDict(
                state=job.ERROR,
                error="simulation is already running",
            )
        o = None
        try:
            # Forced or canceled/errored/missing/invalid so run
            o = self._create_op(
                job.OP_RUN,
                req,
                jobCmd="compute",
                nextRequestSeconds=self.db.nextRequestSeconds,
            )
            t = sirepo.srtime.utc_now_as_int()
            d = self.db
            self.__db_init(req, prev_db=d)
            self.__db_update(
                computeJobQueued=t,
                computeJobSerial=t,
                computeModel=req.content.computeModel,
                # run mode can change between runs so we must update the db
                jobRunMode=req.content.jobRunMode,
                simName=req.content.data.models.simulation.name,
                status=job.PENDING,
            )
            self.pkdel("_sr_exception_in_run")
            self._purged_jids_cache.discard(
                self.__db_file(self.db.computeJid).purebasename
            )
            self.run_op = o
            r = self._status_reply(req)
            if not r:
                raise AssertionError(f"no reply to req={req}")
            o.run_callback = tornado.ioloop.IOLoop.current().call_later(
                0,
                self._run,
                op=o,
                curr_db=self.db,
                prev_db=d,
            )
            o = None
            return r
        except Exception as e:
            if o:
                o.destroy(internal_error=f"_receive_api_runSimulation exception={e}")
            raise

    async def _receive_api_runStatus(self, req):
        r = self._status_reply(req)
        if r:
            return r
        r = await self._send_op_analysis(req, "sequential_result")
        # TODO(robnagler) do we need to check global state?
        if r.state == job.ERROR and "errorCode" not in r:
            # TODO(robnagler) this seems wrong. Should be explicit
            return self._init_db_missing_response(req)
        return r

    async def _receive_api_sbatchLoginStatus(self, req):
        r = False
        o = self._create_op(job.OP_SBATCH_AGENT_READY, req)
        try:
            r = o.assign_driver().agent_is_ready_or_starting()
        finally:
            o.destroy()
        return PKDict(ready=r)

    async def _receive_api_sbatchLogin(self, req):
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

    def _create_op(self, op_name, req, **kwargs):
        req.simulationType = self.db.simulationType
        # run mode can change between runs so use req.content.jobRunMode
        # not self.db.jobRunMode
        r = req.content.get("jobRunMode", self.db.jobRunMode)
        if r not in sirepo.simulation_db.JOB_RUN_MODE_MAP:
            # happens only when config changes, and only when sbatch is missing
            raise sirepo.util.NotFound("invalid jobRunMode={} req={}", r, req)
        kwargs.setdefault(
            "kind",
            (
                job.PARALLEL
                if self.db.isParallel and op_name != job.OP_ANALYSIS
                else job.SEQUENTIAL
            ),
        )
        o = (
            super()
            ._create_op(op_name, req, job_run_mode=r, **kwargs)
            .pkupdate(task=asyncio.current_task())
        )
        self.ops.append(o)
        return o

    def _req_is_valid(self, req):
        return self.db.computeJobHash == req.content.computeJobHash and (
            not req.content.computeJobSerial
            or self.db.computeJobSerial == req.content.computeJobSerial
        )

    async def _run(self, op, curr_db, prev_db):
        def _is_run_op(msg):
            if op == self.run_op:
                return True
            pkdlog("ignore {} op={} because not run_op={}", msg, op, self.run_op)
            return False

        async def _send_op():
            try:
                if not await op.prepare_send() or op.is_destroyed:
                    return False
            except Exception as e:
                if not _is_run_op(f"prepare_send exception={e}"):
                    return False
                if isinstance(e, sirepo.util.SRException) and e.sr_args.params.get(
                    "isSbatchLogin"
                ):
                    pkdlog("isSbatchLogin op={}", op)
                    if curr_db.dbUpdateTime != self.db.dbUpdateTime:
                        pkdlog("update collision jid={}, ignoring", curr_db.computeJid)
                        return False
                    self.__db_update(status=job.MISSING)
                    self._sr_exception_in_run = e
                    return False
                pkdlog("exception={} op={} stack={}", e, op, pkdexc())
                self.__db_update(
                    error="Server error",
                    internalError=op.internal_error or e,
                    status=job.ERROR,
                )
                return False
            # prepare_send may have awaited so need to see if op is still run_op
            if not _is_run_op(f"prepare_send success"):
                return False
            self.__db_update(driverDetails=op.driver.driver_details)
            op.send()
            return True

        if not _is_run_op("start"):
            return
        try:
            op.pkdel("run_callback")
            if not await _send_op():
                return
            with op.set_job_situation("Entered __create._run"):
                while True:
                    if (r := await op.reply_get()) is None:
                        return
                    # TODO(robnagler) is this ever true?
                    # Checked on 1/24/24 and neither check appears in the logs
                    if not _is_run_op(f"reply={r}"):
                        return
                    self.db.queueState = None
                    # run_dir is in a stable state so don't need to lock
                    op.run_dir_slot.free()
                    self.db.status = r.state
                    self.db.alert = r.get("alert")
                    if self.db.status == job.ERROR:
                        self.db.error = r.get("error", "<unknown error>")
                    if "computeJobStart" in r:
                        self.db.computeJobStart = r.computeJobStart
                    if "parallelStatus" in r:
                        self.db.parallelStatus.update(r.parallelStatus)
                        self.db.lastUpdateTime = r.parallelStatus.lastUpdateTime
                    else:
                        # sequential jobs don't send the time so update with local time
                        self.db.lastUpdateTime = sirepo.srtime.utc_now_as_int()
                    # TODO(robnagler) will need final frame count. Not sent?
                    self.__db_write()
                    if r.state in job.EXIT_STATUSES:
                        break
        except Exception as e:
            if _is_run_op(f"_run exception={e}"):
                pkdlog("error={} stack={}", e, pkdexc())
                self.__db_update(
                    status=job.ERROR,
                    internal_error=f"_run exception={e}",
                    error="server error",
                )
        finally:
            op.destroy()

    async def _send_op_analysis(self, req, jobCmd):
        pkdlog(
            "{} api={} method={}",
            req,
            jobCmd,
            req.content.data.get("method"),
        )
        return await self._send_with_single_reply(job.OP_ANALYSIS, req, jobCmd=jobCmd)

    async def _send_with_single_reply(self, op_name, req, **kwargs):
        o = None
        internal_error = None
        try:
            o = self._create_op(op_name, req, **kwargs)
            if not await o.prepare_send() or o.is_destroyed:
                return _canceled_reply()
            o.send()
            if (r := await o.reply_get()) is None:
                return _canceled_reply()
            # POSIT: any api_* that could run into runDirNotFound
            # will call _send_with_single_reply() and this will
            # properly format the reply
            if r.get("runDirNotFound"):
                return self._init_db_missing_response(req)
            return r
        except Exception as e:
            internal_error = f"_send_with_single_reply exception={e}"
            raise
        finally:
            o.destroy(internal_error=internal_error)

    def _status_reply(self, req):
        def res(**kwargs):
            r = PKDict(**kwargs)
            if self.db.canceledAfterSecs is not None:
                r.canceledAfterSecs = self.db.canceledAfterSecs
            if self.db.error:
                r.error = self.db.error
            if self.db.alert:
                r.alert = self.db.alert
            if self.db.isParallel:
                r.update(self.db.parallelStatus)
                r.computeJobHash = self.db.computeJobHash
                r.computeJobSerial = self.db.computeJobSerial
                r.computeModel = self.db.computeModel
                r.elapsedTime = self.elapsed_time()
                r.queueState = self.db.get("queueState")
            if self._is_running_pending():
                c = req.content
                r.update(
                    jobStatusMessage=self.db.jobStatusMessage,
                    nextRequestSeconds=self.db.nextRequestSeconds,
                    nextRequest=PKDict(
                        computeJobHash=self.db.computeJobHash,
                        computeJobSerial=self.db.computeJobSerial,
                        computeJobStart=self.db.computeJobStart,
                        report=c.analysisModel,
                        simulationId=self.db.simulationId,
                        simulationType=self.db.simulationType,
                    ),
                )
            return r

        if self.db.computeJobHash != req.content.computeJobHash:
            return PKDict(state=job.MISSING, reason="computeJobHash-mismatch")
        if (
            req.content.computeJobSerial
            and self.db.computeJobSerial != req.content.computeJobSerial
        ):
            return PKDict(state=job.MISSING, reason="computeJobSerial-mismatch")
        if e := self.pkdel("_sr_exception_in_run"):
            return _exception_reply(e)
        if self.db.isParallel or self.db.status != job.COMPLETED:
            return res(
                state=self.db.status,
                dbUpdateTime=int(self.db.dbUpdateTime),
            )
        return None

    async def _verify_status(self, req):
        self.__db_update(status=job.CANCELED)
        return None

    #
    # rv = await self._send_with_single_reply(
    #     job.OP_VERIFY_STATUS,
    #     req,
    #     kind=job.SEQUENTIAL,
    # )
    # just set canceled so can push out a small pr
    # Need lock on must verify so can check inside lock that still true
    #        if rv.state in
    #        rv.
    #        need lock on job # this is new
    #        do not always send, ask the driver


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
            for x in "run_callback", "timer":
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

    def reply_put(self, reply):
        self._reply_q.put_nowait(reply)

    def send(self):
        async def _timeout():
            pkdlog("{} max_run_secs={}", self, self.max_run_secs)
            await self._supervisor.op_send_timeout(self)

        if self.max_run_secs:
            self.timer = tornado.ioloop.IOLoop.current().call_later(
                self.max_run_secs,
                _timeout,
            )
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
