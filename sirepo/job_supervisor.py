# -*- coding: utf-8 -*-
"""TODO(e-carlin): Doc

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkcollections
from pykern import pkconfig
from pykern import pkinspect
from pykern import pkio
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdc, pkdformat, pkdlog, pkdexc
from sirepo import job
import asyncio
import contextlib
import copy
import datetime
import os
import pykern.pkio
import sirepo.auth
import sirepo.auth_db
import sirepo.http_reply
import sirepo.sim_data
import sirepo.simulation_db
import sirepo.srdb
import sirepo.srtime
import sirepo.tornado
import sirepo.util
import time
import tornado.ioloop
import tornado.locks

#: where supervisor state is persisted to disk
_DB_DIR = None

#: where job db is stored under srdb.root
_DB_SUBDIR = 'supervisor-job'

_NEXT_REQUEST_SECONDS = None

_HISTORY_FIELDS = frozenset((
    'alert',
    'cancelledAfterSecs',
    'computeJobQueued',
    'computeJobSerial',
    'computeJobStart',
    'computeModel'
    'driverDetails',
    'error',
    'internalError',
    'isParallel',
    'isPremiumUser',
    'jobRunMode',
    'jobStatusMessage',
    'lastUpdateTime',
    'status',
))

_PARALLEL_STATUS_FIELDS = frozenset((
    'computeJobHash',
    'computeJobStart',
    'computeModel',
    'elapsedTime',
    'frameCount',
    'lastUpdateTime',
    'percentComplete',
))

_UNTIMED_OPS = frozenset((job.OP_ALIVE, job.OP_CANCEL, job.OP_ERROR, job.OP_KILL, job.OP_OK))
cfg = None

#: how many times restart request when Awaited() raised
_MAX_RETRIES = 10


class Awaited(Exception):
    """An await occurred, restart operation"""
    pass


def init():
    global _DB_DIR, cfg, _NEXT_REQUEST_SECONDS, job_driver
    if _DB_DIR:
        return
    job.init()
    from sirepo import job_driver

    job_driver.init(pkinspect.this_module())
    _DB_DIR = sirepo.srdb.root().join(_DB_SUBDIR)
    cfg = pkconfig.init(
        job_cache_secs=(300, int, 'when to re-read job state from disk'),
        max_hours=dict(
            analysis=(.04, float, 'maximum run-time for analysis job',),
            parallel=(1, float, 'maximum run-time for parallel job (except sbatch)'),
            parallel_premium=(2, float, 'maximum run-time for parallel job for premium user (except sbatch)'),
            sequential=(.1, float, 'maximum run-time for sequential job'),
        ),
        purge_free_after_days=(1000, int, 'how many days to wait before purging a free users simulation'),
        purge_free_start=('02:00:00', str, 'time to first start purging free users simulations (%H:%M:%S)'),
        purge_free_period=('01:00:00', str, 'how often to purge free users simulations after start time (%H:%M:%S)'),
        sbatch_poll_secs=(15, int, 'how often to poll squeue and parallel status'),
    )
    _NEXT_REQUEST_SECONDS = PKDict({
        job.PARALLEL: 2,
        job.SBATCH: cfg.sbatch_poll_secs,
        job.SEQUENTIAL: 1,
    })
    sirepo.auth_db.init(sirepo.srdb.root(), migrate_db_file=False)
    if sirepo.simulation_db.user_dir_name().exists():
        if not _DB_DIR.exists():
            pkdlog('calling upgrade_runner_to_job_db path={}', _DB_DIR)
            import subprocess
            subprocess.check_call(
                (
                    'pyenv',
                    'exec',
                    'sirepo',
                    'db',
                    'upgrade_runner_to_job_db',
                    _DB_DIR,
                ),
                env=PKDict(os.environ).pkupdate(
                    PYENV_VERSION='py2',
                    SIREPO_AUTH_LOGGED_IN_USER='unused',
                ),
            )
    else:
        pykern.pkio.mkdir_parent(_DB_DIR)
    tornado.ioloop.IOLoop.current().add_callback(
        _ComputeJob.purge_free_simulations,
        init=True,
    )


class ServerReq(PKDict):

    def copy_content(self):
        return copy.deepcopy(self.content)

    def pkdebug_str(self):
        c = self.get('content')
        if not c:
            return 'ServerReq(<no content>)'
        return pkdformat('ServerReq({}, {})', c.api, c.get('computeJid'))

    async def receive(self):
        s = self.content.pkdel('serverSecret')
        # no longer contains secret so ok to log
        assert s, \
            'no secret in message: {}'.format(self.content)
        assert s == sirepo.job.cfg.server_secret, \
            'server_secret did not match'.format(self.content)
        self.handler.write(await _ComputeJob.receive(self))


async def terminate():
    from sirepo import job_driver

    await job_driver.terminate()


class _ComputeJob(PKDict):

    instances = PKDict()

    def __init__(self, req, **kwargs):
        super().__init__(
            ops=[],
            run_op=None,
            run_dir_mutex=tornado.locks.Event(),
            **kwargs,
        )
        # At start we don't know anything about the run_dir so assume ready
        self.run_dir_mutex.set()
        self.run_dir_owner = None
        self.pksetdefault(db=lambda: self.__db_init(req))
        self.cache_timeout_set()

    def cache_timeout(self):
        if self.ops:
            self.cache_timeout_set()
        else:
            del self.instances[self.db.computeJid]

    def cache_timeout_set(self):
        self.timer = tornado.ioloop.IOLoop.current().call_later(
            cfg.job_cache_secs,
            self.cache_timeout,
        )

    def clear_status(self, op, exception=None):
        if not exception:
            self.__db_update(jobStatusMessage=None)
            return

    def destroy_op(self, op):
        if op in self.ops:
            self.ops.remove(op)
        if self.run_op == op:
            self.run_op = None
        if op == self.run_dir_owner:
            self.run_dir_release(self.run_dir_owner)

    @classmethod
    def get_instance_or_class(cls, req):
        try:
            j = req.content.computeJid
        except AttributeError:
            return cls
        self = cls.instances.pksetdefault(j, lambda: cls.__create(req))[j]
        # SECURITY: must only return instances for authorized user
        assert req.content.uid == self.db.uid, \
            'req.content.uid={} is not same as db.uid={} for jid={}'.format(
                req.content.uid,
                self.db.uid,
                j,
            )
        return self

    def pkdebug_str(self):
        d = self.get('db')
        if not d:
            return '_ComputeJob()'
        return pkdformat(
            '_ComputeJob({} u={} {} {})',
            d.get('computeJid'),
            d.get('uid'),
            d.get('status'),
            self.ops,
        )

    @classmethod
    async def purge_free_simulations(cls, init=False):
        def _get_uids_and_files():
            r = []
            u = None
            p = sirepo.auth_db.UserRole.uids_of_paid_users()
            for f in pkio.sorted_glob(_DB_DIR.join('*{}'.format(
                    sirepo.simulation_db.JSON_SUFFIX,
            ))):
                n = sirepo.sim_data.uid_from_jid(f.basename)
                if n in p or f.mtime() > _too_old:
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

        def _purge_sim(db_file):
            d = pkcollections.json_load_any(db_file)
            # OPTIMIZATION: We assume the uids_of_paid_users doesn't change very
            # frequently so we don't need to check again. A user could run a sim
            # at anytime so we need to check that they haven't
            if d.lastUpdateTime > _too_old:
                return
            if d.status == job.FREE_USER_PURGED:
                return
            p = sirepo.simulation_db.simulation_run_dir(d)
            pkio.unchecked_remove(p)
            d.status = job.FREE_USER_PURGED
            cls.__db_write_file(d)
            jids_purged.append(db_file.purebasename)

        s = sirepo.srtime.utc_now()
        u = None
        f = None
        try:
            _too_old = sirepo.srtime.utc_now_as_float() - (
                cfg.purge_free_after_days * 24 * 60 * 60
            )

            jids_purged = []
            for u, v in _get_uids_and_files():
                with sirepo.auth.set_user(u):
                    for f in v:
                        _purge_sim(f)
                await tornado.gen.sleep(0)
            pkdlog('jids={}', jids_purged)
        except Exception as e:
            pkdlog('u={} f={} error={} stack={}', u, f, e, pkdexc())
        finally:
            cls._purge_free_simulations_set(s, init)

    @classmethod
    async def receive(cls, req):
        if req.content.get('api') != 'api_runStatus':
            pkdlog('{}', req)
        try:
            o = cls.get_instance_or_class(req)
            return await getattr(
                o,
                '_receive_' + req.content.api,
            )(req)
        except asyncio.CancelledError:
            return PKDict(state=job.CANCELED)
        except Exception as e:
            pkdlog('{} error={} stack={}', req, e, pkdexc())
            return sirepo.http_reply.gen_tornado_exception(e)

    async def run_dir_acquire(self, owner):
        if self.run_dir_owner == owner:
            return
        e = None
        if not self.run_dir_mutex.is_set():
            pkdlog('{} await self.run_dir_mutex', self)
            await self.run_dir_mutex.wait()
            e = Awaited()
            if self.run_dir_owner:
                # some other op acquired it before this one
                raise e
        self.run_dir_mutex.clear()
        self.run_dir_owner = owner
        if e:
            raise e

    def run_dir_release(self, owner):
        assert owner == self.run_dir_owner, \
            'owner={} not same as releaser={}'.format(self.run_dir_owner, owner)
        self.run_dir_owner = None
        self.run_dir_mutex.set()

    def set_status(self, op, status):
        m = None
        if op.opName == job.OP_RUN:
            if status == _Op.STATUS_AWAIT_OP_SLOT:
                m = 'Waiting for another simulation to complete'
            elif status == _Op.STATUS_COMPUTE_RUNNING:
                m = 'Running'

        if m:
            assert not self.db.jobStatusMessage, \
                'Trying to overwrite existing jobStatusMessage={}'.format(
                    self.db.jobStatusMessage,
                )
            self.__db_update(
                jobStatusMessage=m,
            )

    @classmethod
    def __create(cls, req):
        try:
            d = cls.__db_load(req.content.computeJid)
            self = cls(req, db=d)
            if self._is_running_pending():
#TODO(robnagler) when we reconnect with running processes at startup,
#  we'll need to change this
                self.__db_update(status=job.CANCELED)
            return self
        except Exception as e:
            if pykern.pkio.exception_is_not_found(e):
                return cls(req).__db_write()
            raise

    @classmethod
    def __db_file(cls, computeJid):
        return _DB_DIR.join(computeJid + sirepo.simulation_db.JSON_SUFFIX)

    def __db_init(self, req, prev_db=None):
        c = req.content
        self.db = PKDict(
            alert=None,
            cancelledAfterSecs=None,
            computeJid=c.computeJid,
            computeJobHash=c.computeJobHash,
            computeJobSerial=0,
            computeJobStart=0,
            computeJobQueued=0,
            driverDetails=PKDict(),
            error=None,
            jobStatusMessage=None,
            history=self.__db_init_history(prev_db),
            isParallel=c.isParallel,
            isPremiumUser=c.get('isPremiumUser'),
            lastUpdateTime=0,
            simName=None,
            simulationId=c.simulationId,
            simulationType=c.simulationType,
#TODO(robnagler) when would req come in with status?
            status=req.get('status', job.MISSING),
            uid=c.uid,
        )
        r = c.get('jobRunMode')
        if not r:
            assert c.api != 'api_runSimulation', \
                'api_runSimulation must have a jobRunMode content={}'.format(c)
            # __db_init() will be called when runDirNotFound.
            # The api_* that initiated the request may not have
            # a jobRunMode (ex api_downloadDataFile). In that
            # case use the existing jobRunMode because the
            # request doesn't care about the jobRunMode
            r = self.db.jobRunMode

        self.db.pkupdate(
            jobRunMode=r,
            nextRequestSeconds=_NEXT_REQUEST_SECONDS[r],
        )
        if self.db.isParallel:
            self.db.parallelStatus = PKDict(
                ((k, 0) for k in _PARALLEL_STATUS_FIELDS),
            )
        return self.db

    def __db_init_history(self, prev_db):
        if prev_db is None:
            return []
        return prev_db.history + [
            PKDict(((k, v) for k, v in prev_db.items() if k in _HISTORY_FIELDS)),
        ]

    @classmethod
    def __db_load(cls, compute_jid):
        d = pkcollections.json_load_any(
            cls.__db_file(compute_jid),
        )
        for k in [
                'alert',
                'cancelledAfterSecs',
                'isPremiumUser',
                'jobStatusMessage',
                'internalError',
        ]:
            d.setdefault(k, None)
            for h in d.history:
                h.setdefault(k, None)
        return d

    def __db_update(self, **kwargs):
        self.db.pkupdate(**kwargs)
        return self.__db_write()

    def __db_write(self):
        self.__db_write_file(self.db)
        return self

    @classmethod
    def __db_write_file(cls, db):
        sirepo.util.json_dump(db, path=cls.__db_file(db.computeJid))

    @classmethod
    def _get_running_pending_jobs(cls, uid=None):
        def _filter_jobs(job):
            if uid and job.db.uid != uid:
                return False
            return job._is_running_pending()

        def _get_header():
            h = [
                'App',
                'Simulation id',
                'Start (UTC)',
                'Last update (UTC)',
                'Elapsed',
                'Status',
            ]
            if uid:
                h.insert(l, 'Name')
            else:
                h.insert(l, 'User id')
                h.extend([
                    'Queued',
                    'Driver details',
                    'Premium user'
                ])
            return h

        def _strf_unix_time(unix_time):
            return datetime.datetime.utcfromtimestamp(
                int(unix_time),
            ).strftime('%Y-%m-%d %H:%M:%S')

        def _strf_seconds(seconds):
            # formats to [D day[s], ][H]H:MM:SS[.UUUUUU]
            return str(datetime.timedelta(seconds=seconds))

        def _get_rows():
            def _get_queued_time(db):
                m = i.db.computeJobStart if i.db.status == job.RUNNING \
                    else int(time.time())
                return _strf_seconds(m - db.computeJobQueued)

            r = []
            for i in filter(_filter_jobs, cls.instances.values()):
                d = [
                    i.db.simulationType,
                    i.db.simulationId,
                    _strf_unix_time(i.db.computeJobStart),
                    _strf_unix_time(i.db.lastUpdateTime),
                    _strf_seconds(i.db.lastUpdateTime - i.db.computeJobStart),
                    i.db.jobStatusMessage if i.db.jobStatusMessage else '',
                ]
                if uid:
                    d.insert(l, i.db.simName)
                else:
                    d.insert(l, i.db.uid)
                    d.extend([
                        _get_queued_time(i.db),
                        ' | '.join(sorted(i.db.driverDetails.values())),
                        i.db.isPremiumUser,
                    ])
                r.append(d)

            r.sort(key=lambda x: x[l])
            return r

        l = 2
        return PKDict(header=_get_header(), rows=_get_rows())

    def _is_running_pending(self):
        return self.db.status in (job.RUNNING, job.PENDING)

    @classmethod
    async def _receive_api_admJobs(cls, req):
        return cls._get_running_pending_jobs()

    async def _receive_api_downloadDataFile(self, req):
        return await self._send_with_single_reply(
            job.OP_ANALYSIS,
            req,
            jobCmd='download_data_file',
            dataFileKey=req.content.pop('dataFileKey')
        )

    @classmethod
    async def _receive_api_ownJobs(cls, req):
        return cls._get_running_pending_jobs(uid=req.content.uid)

    async def _receive_api_runCancel(self, req, timed_out_op=None):
        """Cancel a run and related ops

        Analysis ops that are for a parallel run (ex. sim frames) will not
        be cancelled.

        Args:
            req (ServerReq): The cancel request
            timed_out_op (_Op, Optional): the op that was timed out, which
                needs to be canceled
        Returns:
            PKDict: Message with state=cancelled
        """

        def _ops_to_cancel():
            r = set(
                o for o in self.ops
                # Do not cancel sim frames. Allow them to come back for a cancelled run
                if not (self.db.isParallel and o.opName == job.OP_ANALYSIS)
            )
            if timed_out_op in self.ops:
                r.add(timed_out_op)
            return list(r)
        r = PKDict(state=job.CANCELED)
        if (
            # a running simulation may be cancelled due to a
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
        c = None
        o = []
        # No matter what happens the job is cancelled
        self.__db_update(status=job.CANCELED)
        self._cancelled_serial = self.db.computeJobSerial
        try:
            for i in range(_MAX_RETRIES):
                try:
                    if _ops_to_cancel():
                        #TODO(robnagler) cancel run_op, not just by jid, which is insufficient (hash)
                        if not c:
                            c = self._create_op(job.OP_CANCEL, req)
                        # do not need to run_dir_acquire. OP_ANALYSIS may be in
                        # process, and it will have run_dir_mutex. That's ok,
                        # because an OP_RUN will wait for run_dir_mutex, and
                        # we'll destroy the OP_RUN below (never getting to the
                        # run_dir_mutex). The opposite case is trickier, but
                        # relies on the fact that we don't preempt below after
                        # the destroy (which may release run_dir_mutex) until the
                        # reply_get await (after the send).
                        await c.prepare_send()
                        o = _ops_to_cancel()
                    elif c:
                        c.destroy()
                        c = None
                    pkdlog('{} cancel={}', self, o)
                    for x in filter(lambda e: e != c, o):
                        x.destroy(cancel=True)
                    if timed_out_op:
                        self.db.cancelledAfterSecs = timed_out_op.maxRunSecs
                    if c:
                        c.msg.opIdsToCancel = [x.opId for x in o]
                        c.send()
                        await c.reply_get()
                    return r
                except Awaited:
                    pass
            else:
                raise AssertionError('too many retries {}'.format(req))
        finally:
            if c:
                c.destroy(cancel=False)

    async def _receive_api_runSimulation(self, req, recursion_depth=0):
        def _set_error(op, compute_job_serial):
            if self.db.computeJobSerial != compute_job_serial:
                # Another run has started
                return
            self.__db_update(
                error='Server error',
                internalError=op.internal_error,
                status=job.ERROR,
            )
            # _run destroys in the happy path (never got to _run here)
            if op:
                op.destroy(cancel=False)

        f = req.content.data.get('forceRun')
        if self._is_running_pending():
            if f or not self._req_is_valid(req):
                return PKDict(
                    state=job.ERROR,
                    error='another browser is running the simulation',
                )
            return PKDict(state=self.db.status)
        if (
            not f
            and self._req_is_valid(req)
            and self.db.status == job.COMPLETED
        ):
            # Valid, completed, transient simulation
            # Read this first https://github.com/radiasoft/sirepo/issues/2007
            r = await self._receive_api_runStatus(req)
            if r.state == job.MISSING:
                # happens when the run dir is deleted (ex _purge_free_simulations)
                assert recursion_depth == 0, \
                    'Infinite recursion detected. Already called from self. req={}'.format(
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
            jobCmd='compute',
            nextRequestSeconds=self.db.nextRequestSeconds,
        )
        t = int(time.time())
        self.__db_init(req, prev_db=self.db)
        self.__db_update(
            computeJobQueued=t,
            computeJobSerial=t,
            computeModel=req.content.computeModel,
            driverDetails=o.driver.driver_details,
            # run mode can change between runs so we must update the db
            jobRunMode=req.content.jobRunMode,
            simName=req.content.data.models.simulation.name,
            status=job.PENDING,
        )
        c = self.db.computeJobSerial
        try:
            for i in range(_MAX_RETRIES):
                try:
                    await self.run_dir_acquire(o)
                    await o.prepare_send()
                    self.run_op = o
                    o.make_lib_dir_symlink()
                    o.send()
                    r = self._status_reply(req)
                    assert r
                    o.run_callback = tornado.ioloop.IOLoop.current().call_later(
                        0,
                        self._run,
                        o,
                    )
                    o = None
                    return r
                except Awaited:
                    pass
            else:
                raise AssertionError('too many retries {}'.format(req))
        except asyncio.CancelledError:
            if self.pkdel('_cancelled_serial') == c:
                # We were cancelled due to api_runCancel.
                # api_runCancel destroyed the op and updated the db
                raise
            # There was a timeout getting the run started. Set the
            # error and let the user know. The timeout has destroyed
            # the op so don't need to in _set_error
            _set_error(None, c)
            return self._status_reply(req)
        except Exception:
            _set_error(o, c)
            raise

    async def _receive_api_runStatus(self, req):
        r = self._status_reply(req)
        if r:
            return r
        return await self._send_with_single_reply(
            job.OP_ANALYSIS,
            req,
            jobCmd='sequential_result',
        )

    async def _receive_api_sbatchLogin(self, req):
        return await self._send_with_single_reply(job.OP_SBATCH_LOGIN, req)

    async def _receive_api_simulationFrame(self, req):
        if not self._req_is_valid(req):
            sirepo.util.raise_not_found('invalid {}', req)
        return await self._send_with_single_reply(
            job.OP_ANALYSIS,
            req,
            jobCmd='get_simulation_frame'
        )

    def _create_op(self, opName, req, **kwargs):
#TODO(robnagler) kind should be set earlier in the queuing process.
        req.kind = job.PARALLEL if self.db.isParallel and opName != job.OP_ANALYSIS \
            else job.SEQUENTIAL
        req.simulationType = self.db.simulationType
        # run mode can change between runs so use req.content.jobRunMode
        # not self.db.jobRunMode
        r = req.content.get('jobRunMode', self.db.jobRunMode)
        if r not in sirepo.simulation_db.JOB_RUN_MODE_MAP:
            # happens only when config changes, and only when sbatch is missing
            sirepo.util.raise_not_found('invalid jobRunMode={} req={}', r, req)
        o = _Op(
#TODO(robnagler) don't like the camelcase. It doesn't actually work right because
# these values are never sent directly, only msg which can be camelcase
            computeJob=self,
            kind=req.kind,
            maxRunSecs=self._get_max_run_secs(
                opName,
                r,
                req,
            ),
            msg=PKDict(req.content).pksetdefault(jobRunMode=r),
            opName=opName,
            req_content=req.copy_content(),
            task=asyncio.current_task(),
        )
        job_driver.assign_instance_op(req, r, o)
        if 'dataFileKey' in kwargs:
            kwargs['dataFileUri'] = job.supervisor_file_uri(
                o.driver.cfg.supervisor_uri,
                job.DATA_FILE_URI,
                kwargs.pop('dataFileKey'),
            )
        o.msg.pkupdate(**kwargs)
        self.ops.append(o)
        return o

    def _get_max_run_secs(self, op_name, run_mode, req):
        if op_name in _UNTIMED_OPS or \
            (run_mode == sirepo.job.SBATCH and op_name == job.OP_RUN):
            return 0
        t = cfg.max_hours[req.kind]
        if op_name == sirepo.job.OP_ANALYSIS:
            t = cfg.max_hours.analysis
        elif req.kind == job.PARALLEL and req.content.get('isPremiumUser'):
            t = cfg.max_hours['parallel_premium']
        return t * 3600

    @classmethod
    def _purge_free_simulations_set(cls, previous_start, init):
        def _call_at(time):
            tornado.ioloop.IOLoop.current().call_at(
                sirepo.srtime.to_timestamp(time),
                _ComputeJob.purge_free_simulations,
            )

        def _get_start():
            t = datetime.datetime.combine(
                datetime.date.fromtimestamp(sirepo.srtime.to_timestamp(n)),
                datetime.datetime.min.time(),
            )
            return t + _get_timedelta(cfg.purge_free_start)

        def _get_timedelta(time_str):
            t = datetime.datetime.strptime(time_str, "%H:%M:%S")
            return datetime.timedelta(
                hours=t.hour,
                minutes=t.minute,
                seconds=t.second,
            )
        n = sirepo.srtime.utc_now()
        s = _get_start()
        p = _get_timedelta(cfg.purge_free_period)

        if not init:
            # TODO(e-carlin): This will drift away from s because
            # call_at doesn't guarantee the callback is called at
            # exactly the time provided. Using previous_start should
            # make the drift inconsequentially small.
            _call_at(previous_start + p)
            return
        if s > n:
            _call_at(s)
            return
        t = s + p
        while t < n:
            t += p
        _call_at(t)

    def _req_is_valid(self, req):
        return (
            self.db.computeJobHash == req.content.computeJobHash
            and (
                not req.content.computeJobSerial or
                self.db.computeJobSerial == req.content.computeJobSerial
            )
        )

    async def _run(self, op):
        op.task = asyncio.current_task()
        op.pkdel('run_callback')
        l = True
        try:
            with op.set_job_status(op.STATUS_COMPUTE_RUNNING):
                while True:
                    try:
                        r = await op.reply_get()
                        #TODO(robnagler) is this ever true?
                        if op != self.run_op:
                            return
                        # run_dir is in a stable state so don't need to lock
                        if l:
                            l = False
                            self.run_dir_release(op)
                        self.db.status = r.state
                        self.db.alert = r.get('alert')
                        if self.db.status == job.ERROR:
                            self.db.error = r.get('error', '<unknown error>')
                        if 'computeJobStart' in r:
                            self.db.computeJobStart = r.computeJobStart
                        if 'parallelStatus' in r:
                            self.db.parallelStatus.update(r.parallelStatus)
                            self.db.lastUpdateTime = r.parallelStatus.lastUpdateTime
                        else:
                            # sequential jobs don't send this
                            self.db.lastUpdateTime = int(time.time())
                        #TODO(robnagler) will need final frame count
                        self.__db_write()
                        if r.state in job.EXIT_STATUSES:
                            break
                    except asyncio.CancelledError:
                        return
        except Exception as e:
            pkdlog('error={} stack={}', e, pkdexc())
            if op == self.run_op:
                self.__db_update(
                    status=job.ERROR,
                    error='server error',
                )
        finally:
            op.destroy(cancel=False)

    async def _send_with_single_reply(self, opName, req, **kwargs):
        o = self._create_op(opName, req, **kwargs)
        try:
            for i in range(_MAX_RETRIES):
                try:
                    if opName == job.OP_ANALYSIS:
                        await self.run_dir_acquire(o)
                    await o.prepare_send()
                    o.send()
                    r =  await o.reply_get()
                    # POSIT: any api_* that could run into runDirNotFound
                    # will call _send_with_single_reply() and this will
                    # properly format the reply
                    if not r.get('runDirNotFound'):
                        return r
                    self.__db_init(req, prev_db=self.db)
                    assert self.db.status == job.MISSING, \
                        'expecting missing status={}'.format(self.db.status)
                    return PKDict(state=self.db.status)
                except Awaited:
                    pass
            else:
                raise AssertionError('too many retries {}'.format(req))
        finally:
            o.destroy(cancel=False)

    def _status_reply(self, req):
        def res(**kwargs):
            r = PKDict(**kwargs)
            if self.db.cancelledAfterSecs is not None:
                r.cancelledAfterSecs = self.db.cancelledAfterSecs
            if self.db.error:
                r.error = self.db.error
            if self.db.alert:
                r.alert = self.db.alert
            if self.db.isParallel:
                r.update(self.db.parallelStatus)
                r.computeJobHash = self.db.computeJobHash
                r.computeJobSerial = self.db.computeJobSerial
                r.elapsedTime = self.db.lastUpdateTime - self.db.computeJobStart
            if self._is_running_pending():
                c = req.content
                r.update(
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
            return PKDict(state=job.MISSING, reason='computeJobHash-mismatch')
        if (
            req.content.computeJobSerial and
            self.db.computeJobSerial != req.content.computeJobSerial
        ):
            return PKDict(state=job.MISSING, reason='computeJobSerial-mismatch')
        if self.db.isParallel or self.db.status != job.COMPLETED:
            return res(state=self.db.status)
        return None


class _Op(PKDict):
    STATUS_AWAIT_OP_SLOT = 'status_await_op_slot'
    STATUS_COMPUTE_RUNNING = 'status_compute_running'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.update(
            do_not_send=False,
            internal_error=None,
            opId=job.unique_key(),
            _reply_q=sirepo.tornado.Queue(),
        )
        self.msg.update(opId=self.opId, opName=self.opName)
        pkdlog('{} runDir={}', self, self.msg.get('runDir'))

    def destroy(self, cancel=True, internal_error=None):
        if cancel:
            if self.task:
                self.task.cancel()
                self.task = None
        # Ops can be destroyed multiple times
        # The first error is "closest to the source" so don't overwrite it
        if not self.internal_error:
            self.internal_error = internal_error
        for x in 'run_callback', 'timer':
            if x in self:
                tornado.ioloop.IOLoop.current().remove_timeout(self.pkdel(x))
        if 'lib_dir_symlink' in self:
            # lib_dir_symlink is unique_key so not dangerous to remove
            pykern.pkio.unchecked_remove(self.pkdel('lib_dir_symlink'))
        self.computeJob.destroy_op(self)
        self.driver.destroy_op(self)

    def make_lib_dir_symlink(self):
        self.driver.make_lib_dir_symlink(self)

    def pkdebug_str(self):
        return pkdformat('_Op({}, {:.4})', self.opName, self.opId)

    async def prepare_send(self):
        """Ensures resources are available for sending to agent

        To maintain consistency, do not modify global state before
        calling this method.
        """
        await self.driver.prepare_send(self)

    async def reply_get(self):
        # If we get an exception (cancelled), task is not done.
        # Had to look at the implementation of Queue to see that
        # task_done should only be called if get actually removes
        # the item from the queue.
        pkdlog('{} await _reply_q.get()', self)
        r = await self._reply_q.get()
        self._reply_q.task_done()
        return r

    def reply_put(self, reply):
        self._reply_q.put_nowait(reply)

    async def run_timeout(self):
        """Can be any op that's timed"""
        pkdlog('{} maxRunSecs={}', self, self.maxRunSecs)
        await self.computeJob._receive_api_runCancel(
            ServerReq(content=self.req_content),
            timed_out_op=self,
        )

    def send(self):
        if self.maxRunSecs:
            self.timer = tornado.ioloop.IOLoop.current().call_later(
                self.maxRunSecs,
                self.run_timeout,
            )
        self.driver.send(self)

    @contextlib.contextmanager
    def set_job_status(self, status):
        self.computeJob.set_status(self, status)
        try:
            yield
            self.computeJob.clear_status(self)
        except Exception as e:
            self.computeJob.clear_status(self, exception=e)
            raise

    def __hash__(self):
        return hash((self.opId,))
