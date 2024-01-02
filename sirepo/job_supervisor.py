# -*- coding: utf-8 -*-
"""TODO(e-carlin): Doc

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern import pkcollections
from pykern import pkconfig
from pykern import pkio
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdc, pkdformat, pkdlog, pkdexc
from sirepo import job
import asyncio
import contextlib
import copy
import enum
import pykern.pkio
import sirepo.const
import sirepo.global_resources
import sirepo.quest
import sirepo.simulation_db
import sirepo.srdb
import sirepo.srtime
import sirepo.tornado
import sirepo.util
import tornado.ioloop
import tornado.locks

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


class SlotAllocStatus(enum.Enum):
    DID_NOT_AWAIT = 1
    HAD_TO_AWAIT = 2


class ServerReq(PKDict):
    def copy_content(self):
        return copy.deepcopy(self.content)

    def pkdebug_str(self):
        c = self.get("content")
        if not c:
            return "ServerReq(<no content>)"
        return pkdformat("ServerReq({}, {})", c.api, c.get("computeJid"))

    async def receive(self):
        s = self.content.pkdel("serverSecret")
        # no longer contains secret so ok to log
        assert s, "no secret in message content={}".format(self.content)
        assert (
            s == sirepo.job.cfg().server_secret
        ), "server_secret did not match content={}".format(self.content)
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
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def destroy_op(self, op):
        pass

    @classmethod
    def get_compute_job_or_self(cls, req):
        try:
            j = req.content.computeJid
        except AttributeError:
            return cls(req=req)
        self = _ComputeJob.instances.pksetdefault(j, lambda: _ComputeJob.create(req))[j]
        # SECURITY: must only return instances for authorized user
        assert (
            req.content.uid == self.db.uid
        ), "req.content.uid={} is not same as db.uid={} for jid={}".format(
            req.content.uid,
            self.db.uid,
            j,
        )
        return self

    def pkdebug_str(self):
        return pkdformat(
            "_Supervisor(api={} uid={})", self.req.content.api, self.req.content.uid
        )

    @classmethod
    async def receive(cls, req):
        if req.content.get("api") != "api_runStatus":
            pkdlog("{}", req)
        try:
            o = cls.get_compute_job_or_self(req)
            return await getattr(
                o,
                "_receive_" + req.content.api,
            )(req)
        except sirepo.const.ASYNC_CANCELED_ERROR:
            return PKDict(state=job.CANCELED)
        except Exception as e:
            pkdlog("{} error={} stack={}", req, e, pkdexc())
            if isinstance(e, sirepo.util.ReplyExc):
                return cls._reply_exception(e)
            raise

    async def op_run_timeout(self, op):
        pass

    def _create_op(self, op_name, req, kind, job_run_mode, **kwargs):
        req.kind = kind
        return _Op(
            _supervisor=self,
            kind=req.kind,
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
        c = self._create_op(job.OP_BEGIN_SESSION, req, job.SEQUENTIAL, "sequential")
        try:
            await c.prepare_send()
        finally:
            c.destroy(cancel_task=False)
        return PKDict()

    async def _receive_api_globalResources(self, req):
        return sirepo.global_resources.for_simulation(
            req.content.data.simulationType,
            req.content.data.simulationId,
            uid=req.content.uid,
        )

    async def _receive_api_ownJobs(self, req):
        return self._get_running_pending_jobs(uid=req.content.uid)

    @classmethod
    def _reply_exception(cls, exc):
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


class _ComputeJob(_Supervisor):
    instances = PKDict()
    _purged_jids_cache = set()

    def __init__(self, req, **kwargs):
        super().__init__(
            ops=[],
            run_op=None,
            run_dir_slot_q=SlotQueue(),
            **kwargs,
        )
        # At start we don't know anything about the run_dir so assume ready
        self.pksetdefault(db=lambda: self.__db_init(req))
        self.cache_timeout_set()

    def cache_timeout(self):
        if self.ops:
            self.cache_timeout_set()
        else:
            del self.instances[self.db.computeJid]

    def cache_timeout_set(self):
        self.timer = tornado.ioloop.IOLoop.current().call_later(
            _cfg.job_cache_secs,
            self.cache_timeout,
        )

    @classmethod
    def create(cls, req):
        try:
            d = cls.__db_load(req.content.computeJid)
            self = cls(req, db=d)
            if self._is_running_pending():
                # TODO(robnagler) when we reconnect with running processes at startup,
                #  we'll need to change this
                self.__db_update(status=job.CANCELED)
            return self
        except Exception as e:
            if pykern.pkio.exception_is_not_found(e):
                return cls(req).__db_write()
            raise

    def destroy_op(self, op):
        if op in self.ops:
            self.ops.remove(op)
        if self.run_op == op:
            self.run_op = None

    def elapsed_time(self):
        if not self.db.computeJobStart:
            return 0
        return (
            sirepo.srtime.utc_now_as_int()
            if self._is_running_pending()
            else self.db.dbUpdateTime
        ) - self.db.computeJobStart

    async def op_run_timeout(self, op):
        await self._receive_api_runCancel(
            ServerReq(content=op.msg),
            timed_out_op=op,
        )

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
    async def purge_non_premium(cls):
        def _get_uids_and_files(qcall):
            r = []
            u = None
            p = qcall.auth_db.model("UserRole").uids_of_paid_users()
            for f in pkio.sorted_glob(
                _DB_DIR.join(
                    f"*{sirepo.const.JSON_SUFFIX}",
                )
            ):
                n = sirepo.job.split_jid(jid=f.purebasename).uid
                if (
                    n in p
                    or f.mtime() > _too_old
                    or f.purebasename in cls._purged_jids_cache
                ):
                    continue
                if u != n:
                    # POSIT: Uid is the first part of each db file. The files are
                    # sorted so this should yield all of a user's files
                    if r:
                        yield u, r
                    u = n
                    r = []
                r.append(f)
            if r:
                yield u, r

        def _purge_job(jid, qcall):
            d = cls.__db_load(jid)
            if d.lastUpdateTime > _too_old:
                return
            cls._purged_jids_cache.add(jid)
            if d.status == job.JOB_RUN_PURGED or not sirepo.util.is_sim_type(
                d.simulationType
            ):
                return
            try:
                pkio.unchecked_remove(
                    sirepo.simulation_db.simulation_run_dir(d, qcall=qcall)
                )
            except sirepo.util.UserDirNotFound:
                pass
            n = cls.__db_init_new(d, d)
            n.status = job.JOB_RUN_PURGED
            cls.__db_write_file(n)
            pkdlog("jid={}", jid)

        if not _cfg.purge_check_interval:
            return
        s = sirepo.srtime.utc_now()
        u = None
        f = None
        try:
            _too_old = sirepo.srtime.utc_now_as_int() - _cfg.run_dir_lifetime
            with sirepo.quest.start() as qcall:
                for u, v in _get_uids_and_files(qcall):
                    with qcall.auth.logged_in_user_set(u):
                        for f in v:
                            _purge_job(jid=f.purebasename, qcall=qcall)
                    await tornado.gen.sleep(0)
        except Exception as e:
            pkdlog("u={} f={} error={} stack={}", u, f, e, pkdexc())
        finally:
            tornado.ioloop.IOLoop.current().call_later(
                _cfg.purge_check_interval,
                cls.purge_non_premium,
            )

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
    def __db_file(cls, computeJid):
        return _DB_DIR.join(
            sirepo.simulation_db.assert_sim_db_file_path(computeJid)
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
            dbUpdateTime=sirepo.srtime.utc_now_as_int(),
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
        f = cls.__db_file(compute_jid)
        d = pkcollections.json_load_any(f)
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
            dbUpdateTime=lambda: f.mtime(),
        )
        if "cancelledAfterSecs" in d:
            d.canceledAfterSecs = d.pkdel("cancelledAfterSecs", default=v)
            for h in d.history:
                h.canceledAfterSecs = d.pkdel("cancelledAfterSecs", default=v)
        return d

    def __db_restore(self, db):
        self.db = db
        self.__db_write()

    def __db_update(self, **kwargs):
        self.db.pkupdate(**kwargs)
        return self.__db_write()

    def __db_write(self):
        self.db.dbUpdateTime = sirepo.srtime.utc_now_as_int()
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
        self._raise_if_purged_or_missing(req)
        return await self._send_with_single_reply(
            job.OP_IO,
            req,
            jobCmd="download_data_file",
        )

    async def _receive_api_runCancel(self, req, timed_out_op=None):
        """Cancel a run and related ops

        Analysis ops that are for a parallel run (ex. sim frames) will not
        be canceled.

        Args:
            req (ServerReq): The cancel request
            timed_out_op (_Op, Optional): the op that was timed out, which
                needs to be canceled
        Returns:
            PKDict: Message with state=canceled
        """

        def _ops_to_cancel():
            r = set(
                o
                for o in self.ops
                # Do not cancel sim frames and file requests. Allow them to come back for a canceled
                # compute job. Both can have relevant data in the event of a canceled compute job.
                # In the case of OP_IO we excpect that the only reason for cancelation is due to
                # a timeout (max_run_secs reached) in which case we send back "content-too-large".
                if not (
                    self.db.isParallel and o.op_name in (job.OP_ANALYSIS, job.OP_IO)
                )
            )
            if timed_out_op in self.ops:
                r.add(timed_out_op)
            return r

        r = PKDict(state=job.CANCELED)
        if (
            # a running simulation may be canceled due to a
            # downloadDataFile request timeout in another browser window (only the
            # computeJids must match between the two requests). This might be
            # a weird UX but it's important to do, because no op should take
            # longer than its timeout.
            #
            # timed_out_op might not be a valid request, because a new compute
            # may have been started so either we are canceling a compute by
            # user directive (left) or timing out an op (and canceling all).
            (not self._req_is_valid(req) and not timed_out_op)
            or (not self._is_running_pending() and not self.ops)
        ):
            # job is not relevant, but let the user know it isn't running
            return r
        internal_error = None
        candidates = _ops_to_cancel()
        # must be after candidates so don't cancel "c"
        c = self._create_op(job.OP_CANCEL, req)
        # No matter what happens the job is canceled
        self.__db_update(status=job.CANCELED)
        self._canceled_serial = self.db.computeJobSerial
        try:
            # TODO(robnagler) cancel run_op, not just by jid, which is insufficient (hash)
            await c.prepare_send()
            # Only cancel "old" ops. New ones should not be affected by this cancel.
            o = _ops_to_cancel().intersection(candidates)
            if not o:
                return
            pkdlog("{} to_cancel={}", self, o)
            if timed_out_op:
                self.__db_update(canceledAfterSecs=timed_out_op.max_run_secs)
            for x in o:
                x.destroy(cancel_task=True)
            c.msg.opIdsToCancel = [x.op_id for x in o]
            c.send()
            await c.reply_get()
            return r
        except Exception as e:
            internal_error = f"_run exception={e}"
        finally:
            c.destroy(cancel_task=False, internal_error=internal_error)

    async def _receive_api_runSimulation(self, req, recursion_depth=0):
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
                assert (
                    recursion_depth == 0
                ), "Infinite recursion detected. Already called from self. req={}".format(
                    req,
                )
                return await self._receive_api_runSimulation(
                    req,
                    recursion_depth + 1,
                )
            return r
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
        self._purged_jids_cache.discard(self.__db_file(self.db.computeJid).purebasename)
        self.run_op = o
        r = self._status_reply(req)
        assert r
        o.run_callback = tornado.ioloop.IOLoop.current().call_later(
            0,
            self._run,
            o,
            self.db.computeJobSerial,
            d,
        )
        o = None
        return r

    async def _receive_api_runStatus(self, req):
        if "_sr_exception" in self:
            raise self.pkdel("_sr_exception")
        r = self._status_reply(req)
        if r:
            return r
        r = await self._send_op_analysis(req, "sequential_result")
        if r.state == job.ERROR and "errorCode" not in r:
            return self._init_db_missing_response(req)
        return r

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
        k = (
            job.PARALLEL
            if self.db.isParallel and op_name != job.OP_ANALYSIS
            else job.SEQUENTIAL
        )
        o = (
            super()
            ._create_op(op_name, req, k, r, **kwargs)
            .pkupdate(task=asyncio.current_task())
        )
        self.ops.append(o)
        return o

    def _req_is_valid(self, req):
        return self.db.computeJobHash == req.content.computeJobHash and (
            not req.content.computeJobSerial
            or self.db.computeJobSerial == req.content.computeJobSerial
        )

    async def _run(self, op, compute_job_serial, prev_db):
        def _set_error(compute_job_serial, internal_error):
            if self.db.computeJobSerial != compute_job_serial:
                # Another run has started
                return
            self.__db_update(
                error="Server error",
                internalError=internal_error,
                status=job.ERROR,
            )

        async def _send_op(op, compute_job_serial, prev_db):
            try:
                await op.prepare_send()
            except sirepo.const.ASYNC_CANCELED_ERROR:
                if self.pkdel("_canceled_serial") != compute_job_serial:
                    # There was a timeout getting the run started. Set the
                    # error and let the user know. The timeout has destroyed
                    # the op so don't need to destroy here
                    _set_error(compute_job_serial, op.internal_error)
                else:
                    # We were canceled due to api_runCancel.
                    # api_runCancel destroyed the op and updated the db
                    pass
                raise
            except Exception as e:
                op.destroy(cancel_task=False, internal_error=f"_send_op exception={e}")
                if isinstance(e, sirepo.util.SRException) and e.sr_args.params.get(
                    "isGeneral"
                ):
                    self.__db_restore(prev_db)
                    self._sr_exception = e
                    return False
                _set_error(compute_job_serial, op.internal_error)
                raise
            self.__db_update(driverDetails=op.driver.driver_details)
            op.make_lib_dir_symlink()
            op.send()
            return True

        op.task = asyncio.current_task()
        op.pkdel("run_callback")
        await _send_op(op, compute_job_serial, prev_db)
        try:
            with op.set_job_situation("Entered __create._run"):
                while True:
                    try:
                        r = await op.reply_get()
                        self.db.queueState = None
                        # TODO(robnagler) is this ever true?
                        if op != self.run_op:
                            pkdlog(
                                "ignore op={} because not run_op={}", op, self.run_op
                            )
                            return
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
                            # sequential jobs don't send this
                            self.db.lastUpdateTime = sirepo.srtime.utc_now_as_int()
                        # TODO(robnagler) will need final frame count
                        self.__db_write()
                        if r.state in job.EXIT_STATUSES:
                            break
                    except sirepo.const.ASYNC_CANCELED_ERROR:
                        self.db.queueState = None
                        return
        except Exception as e:
            pkdlog("error={} stack={}", e, pkdexc())
            if op == self.run_op:
                self.__db_update(
                    status=job.ERROR,
                    internal_error=f"_run exception={e}",
                    error="server error",
                )
            else:
                pkdlog("no db_update op={} because not run_op={}", op, self.run_op)

        finally:
            op.destroy(cancel_task=False)

    async def _send_op_analysis(self, req, jobCmd):
        pkdlog(
            "{} api={} method={}",
            req,
            jobCmd,
            req.content.data.get("method"),
        )

        return await self._send_with_single_reply(job.OP_ANALYSIS, req, jobCmd=jobCmd)

    async def _send_with_single_reply(self, op_name, req, **kwargs):
        o = self._create_op(op_name, req, **kwargs)
        internal_error = None
        try:
            await o.prepare_send()
            o.send()
            r = await o.reply_get()
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
            o.destroy(cancel_task=False, internal_error=internal_error)

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
        if self.db.isParallel or self.db.status != job.COMPLETED:
            return res(
                state=self.db.status,
                dbUpdateTime=self.db.dbUpdateTime,
            )
        return None


class _Op(PKDict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.update(
            do_not_send=False,
            internal_error=None,
            op_id=job.unique_key(),
            _reply_q=sirepo.tornado.Queue(),
        )
        if "run_dir_slot_q" in self._supervisor:
            self.run_dir_slot = self._supervisor.run_dir_slot_q.sr_slot_proxy(self)
        self.msg.update(opId=self.op_id, opName=self.op_name)
        pkdlog("{} runDir={}", self, self.msg.get("runDir"))

    def destroy(self, cancel_task=True, internal_error=None):
        if x := self.pkdel("run_dir_slot"):
            x.free()
        if (x := self.pkdel("task")) and cancel_task:
            x.cancel()
        for x in "run_callback", "timer":
            if y := self.pkdel(x):
                tornado.ioloop.IOLoop.current().remove_timeout(y)
        # Ops can be destroyed multiple times
        # The first error is "closest to the source" so don't overwrite it
        if internal_error and not self.internal_error:
            self.internal_error = internal_error
        self._supervisor.destroy_op(self)
        self.driver.destroy_op(self)
        self.driver = None

    def make_lib_dir_symlink(self):
        self.driver.make_lib_dir_symlink(self)

    def pkdebug_str(self):
        def _internal_error():
            if not self.internal_error:
                return ""
            return ", internal_error={self.internal_error}"

        return pkdformat(
            "_Op({}, {:.4}{})", self.op_name, self.op_id, _internal_error()
        )

    async def prepare_send(self):
        """Ensures resources are available for sending to agent
        To maintain consistency, do not modify global state before
        calling this method.
        """
        if "driver" not in self:
            self.driver = job_driver.assign_instance_op(self)
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
        await self.driver.prepare_send(self)

    async def reply_get(self):
        # If we get an exception (canceled), task is not done.
        # Had to look at the implementation of Queue to see that
        # task_done should only be called if get actually removes
        # the item from the queue.
        pkdlog("{} await _reply_q.get()", self)
        r = await self._reply_q.get()
        self._reply_q.task_done()
        return r

    def reply_put(self, reply):
        self._reply_q.put_nowait(reply)

    async def run_timeout(self):
        """Can be any op that's timed"""
        pkdlog("{} max_run_secs={}", self, self.max_run_secs)
        # TODO add-qcall and pass to op, can't be Op() or Supervisor()
        await self._supervisor.op_run_timeout(self)

    def send(self):
        if self.max_run_secs:
            self.timer = tornado.ioloop.IOLoop.current().call_later(
                self.max_run_secs,
                self.run_timeout,
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
