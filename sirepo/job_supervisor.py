# -*- coding: utf-8 -*-
"""TODO(e-carlin): Doc

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkcollections
from pykern import pkconfig
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdc, pkdlog, pkdexc
from sirepo import job
from sirepo import job_driver
import os
import pykern.pkio
import sirepo.srdb
import sirepo.util
import time
import tornado.ioloop
import tornado.locks


#: where supervisor state is persisted to disk
_DB_DIR = None

#: where job db is stored under srdb.root
_DB_SUBDIR = 'supervisor-job'

_NEXT_REQUEST_SECONDS = None

_RUNNING_PENDING = (job.RUNNING, job.PENDING)

_HISTORY_FIELDS = frozenset((
    'computeJobStart',
    'computeJobQueued',
    'error',
    'jobRunMode',
    'lastUpdateTime',
    'status',
))

_PARALLEL_STATUS_FIELDS = frozenset((
    'computeJobHash',
    'elapsedTime',
    'frameCount',
    'lastUpdateTime',
    'percentComplete',
    'computeJobStart',
))

cfg = None

def init():
    global _DB_DIR, cfg, _NEXT_REQUEST_SECONDS
    if _DB_DIR:
        return
    job.init()
    job_driver.init()
    _DB_DIR = sirepo.srdb.root().join(_DB_SUBDIR)
    pykern.pkio.mkdir_parent(_DB_DIR)
    cfg = pkconfig.init(
        sbatch_poll_secs=(60, int, 'how often to poll squeue and parallel status'),
    )
    _NEXT_REQUEST_SECONDS = PKDict({
        job.PARALLEL: 2,
        job.SBATCH: cfg.sbatch_poll_secs,
        job.SEQUENTIAL: 1,
    })


class ServerReq(PKDict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.uid = self.content.uid
        self._response = None
        self._response_received = tornado.locks.Event()

    async def receive(self):
        s = self.content.pkdel('serverSecret')
        # no longer contains secret so ok to log
        assert s, \
            'no secret in message: {}'.format(self.content)
        assert s == sirepo.job.server_secret, \
            'server_secret did not match'.format(self.content)
        self.handler.write(await _ComputeJob.receive(self))


async def terminate():
    await job_driver.terminate()


class _ComputeJob(PKDict):

    instances = PKDict()

    def __init__(self, req, **kwargs):
        c = req.content
        super().__init__(_ops=[], _sent_run=False, **kwargs)
        self.pksetdefault(db=lambda: self.__db_init(req))

    def destroy_op(self, op):
        self._ops.remove(op)
        op.destroy()

    @classmethod
    def get_instance(cls, req):
        j = req.content.computeJid
        self = cls.instances.pksetdefault(j, lambda: cls.__create(req))[j]
        # SECURITY: must only return instances for authorized user
        assert req.content.uid == self.db.uid, \
            'req.content.uid={} is not same as db.uid={} for jid={}'.format(
                req.content.uid,
                self.db.uid,
                j,
            )
        return self

    @classmethod
    async def receive(cls, req):
        pkdlog('{} jid={}', req.content.api, req.content.get('computeJid'))
        return await getattr(
            cls.get_instance(req),
            '_receive_' + req.content.api,
        )(req)

    @classmethod
    def __create(cls, req):
        try:
            d = pkcollections.json_load_any(
                cls.__db_file(req.content.computeJid),
            )
#TODO(robnagler) when we reconnet with running processes at startup,
#  we'll need to change this
            if d.status in _RUNNING_PENDING:
                d.status = job.CANCELED
            return cls(req, db=d)
        except Exception as e:
            if pykern.pkio.exception_is_not_found(e):
                return cls(req).__db_write()
            raise

    @classmethod
    def __db_file(cls, computeJid):
        return _DB_DIR.join(computeJid + '.json')

    def __db_init(self, req, prev_db=None):
        c = req.content
        self.db = PKDict(
            computeJid=c.computeJid,
            computeJobHash=c.computeJobHash,
            computeJobStart=0,
            computeJobQueued=0,
            error=None,
            history=self.__db_init_history(prev_db),
            isParallel=c.isParallel,
            jobRunMode=c.jobRunMode,
            lastUpdateTime=0,
            nextRequestSeconds=_NEXT_REQUEST_SECONDS[c.jobRunMode],
            simulationId=c.simulationId,
            simulationType=c.simulationType,
#TODO(robnagler) when would req come in with status?
            status=req.get('status', job.MISSING),
            uid=c.uid,
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

    def __db_write(self):
        sirepo.util.json_dump(self.db, path=self.__db_file(self.db.computeJid))
        return self

    async def _receive_api_downloadDataFile(self, req):
        await self._send_with_single_reply(
            job.OP_ANALYSIS,
            req,
            jobCmd='get_data_file',
        )

    async def _receive_api_runCancel(self, req):
        r = PKDict(state=job.CANCELED)
        if self.db.computeJobHash != req.content.computeJobHash:
            # not our job, but let the user know it isn't running
            return r
        if self._sent_run:
            await self._send_with_single_reply(
                job.OP_CANCEL,
                req,
            )
        self.db.status = job.CANCELED
        for o in self._ops:
            if o.msg.computeJid == req.content.computeJid:
                o.set_canceled()
        self.__db_write()
        return r

    async def _receive_api_runSimulation(self, req):
        if self.db.status == _RUNNING_PENDING:
            if self.db.computeJobHash != req.content.computeJobHash:
#TODO(robnagler) need to deal with double clicks
#TODO(robnagler) do transient/sequential sims runSim without a cancel? I think we
#  should require the GUI to cancel before running so would return an error here
                raise AssertionError('FIXME')
            return PKDict(state=job.RUNNING)
        if (self.db.computeJobHash != req.content.computeJobHash
            or self.db.status != job.COMPLETED
        ):
            self.__db_init(req, prev_db=self.db)
            self.db.computeJobQueued = int(time.time())
            self.db.pkupdate(status=job.PENDING)
            self.__db_write()
            tornado.ioloop.IOLoop.current().add_callback(self._run, req)
        # Read this first https://github.com/radiasoft/sirepo/issues/2007
        return await self._receive_api_runStatus(req)

    async def _receive_api_runStatus(self, req):
        def res(**kwargs):
            r = PKDict(**kwargs)
            if self.db.error:
                r.error = self.db.error
            if self.db.isParallel:
                r.update(self.db.parallelStatus)
                r.computeJobHash = self.db.computeJobHash
                r.computeJobStart = self.db.computeJobStart
                r.elapsedTime = r.lastUpdateTime - r.computeJobStart
            if self.db.status in _RUNNING_PENDING:
                c = req.content
                r.update(
                    nextRequestSeconds=self.db.nextRequestSeconds,
                    nextRequest=PKDict(
                        computeJobHash=self.db.computeJobHash,
                        report=c.analysisModel,
                        simulationId=self.db.simulationId,
                        simulationType=self.db.simulationType,
                    ),
                )
            return r
        if self.db.computeJobHash != req.content.computeJobHash:
            return res(state=job.MISSING)
        if self.db.isParallel or self.db.status != job.COMPLETED:
            return res(state=self.db.status)
        return await self._send_with_single_reply(
            job.OP_ANALYSIS,
            req,
            jobCmd='sequential_result',
        )

    async def _receive_api_simulationFrame(self, req):
        assert self.db.computeJobHash == req.content.computeJobHash, \
            'expected computeJobHash={} but got={}'.format(
                self.db.computeJobHash,
                req.content.computeJobHash,
            )
        return await self._send_with_single_reply(
            job.OP_ANALYSIS,
            req,
            'get_simulation_frame'
        )

    async def _run(self, req):
        if self.db.computeJobHash != req.content.computeJobHash:
            pkdlog(
                'invalid computeJobHash self={} req={}',
                self.db.computeJobHash,
                req.content.computeJobHash
            )
#TODO(robnagler) ensure the request is replied to
            self.destroy_op(op)
            return
        o = await self._send(
            job.OP_RUN,
            req,
            jobCmd='compute',
            nextRequestSeconds=self.db.nextRequestSeconds,
        )
        # TODO(e-carlin): XXX bug. If cancel comes in then self.db.status = canceled
        # This overwrites it, but there is a state=canceled message waiting for
        # us in the reply_ready q. We then await o.reply_ready() and get the cancel
        # message then set self.db.status back to canceled. This works because the
        # await o.reply_ready() doesn't block because there is a cancel message
        # in the q
#TODO(robnagler) need to assert that this is still our job
#TODO(robnagler) this is a general problem: after await: check ownership
        self._sent_run = True
        while True:
            r = await o.reply_ready()
            if r.state == job.CANCELED:
                break
            self.db.status = r.state
            if self.db.status == job.ERROR:
                self.db.error = r.get('error', '<unknown error>')
            if 'computeJobStart' in r:
                self.db.computeJobStart = r.computeJobStart
            if 'parallelStatus' in r:
#rjn i removed the assert, because the parallelStatus.update will do the trick
                self.db.parallelStatus.update(r.parallelStatus)
                self.db.lastUpdateTime = r.parallelStatus.lastUpdateTime
            else:
                # sequential jobs don't send this
                self.db.lastUpdateTime = int(time.time())
                #TODO(robnagler) will need final frame count
            self.__db_write()
            # TODO(e-carlin): What if this never comes?
            if r.state in job.EXIT_STATUSES:
                break
        pkdlog('destroy_op={}', o.opId)
        self.destroy_op(o)

    async def _send(self, opName, req, jobCmd, **kwargs):
        # TODO(e-carlin): proper error handling
        try:
#TODO(robnagler) kind should be set earlier in the queuing process.
            req.kind = job.PARALLEL if self.db.isParallel and opName != job.OP_ANALYSIS \
                else job.SEQUENTIAL
            req.simulationType = self.db.simulationType
            # TODO(e-carlin): We need to be able to cancel requests waiting in this
            # state. Currently we assume that all requests get a driver and the
            # code does not block.
            d = await job_driver.get_instance(req, self.db.jobRunMode)
            o = _Op(
                driver=d,
                msg=PKDict(
                    req.content
                ).pkupdate(
                    jobCmd=jobCmd,
                    **kwargs,
                ).pksetdefault(jobRunMode=self.db.jobRunMode),
                opName=opName,
            )
            self._ops.append(o)
            await d.send(o)
            return o
        except Exception as e:
            pkdlog('error={} stack={}', e, pkdexc())

    async def _send_with_single_reply(self, opName, req, jobCmd=None):
        o = await self._send(opName, req, jobCmd)
        r = await o.reply_ready()
        assert r.state in job.EXIT_STATUSES
        self.destroy_op(o)
        return r


class _Op(PKDict):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.update(
            opId=job.unique_key(),
            send_ready=tornado.locks.Event(),
            canceled=False,
            errored=False,
            _reply_q=tornado.queues.Queue(),
        )
        self.msg.update(opId=self.opId, opName=self.opName)

    def set_canceled(self):
        self.canceled = True
        self.reply_put(PKDict(state=job.CANCELED))
        self.send_ready.set()
        self.driver.cancel_op(self)

    def set_errored(self, error):
        self.errored = True
        self.reply_put(
            PKDict(state=job.ERROR, error=error),
        )
        self.send_ready.set()

    def destroy(self):
        self.driver.destroy_op(self)

    def reply_put(self, msg):
        self._reply_q.put_nowait(msg)

    async def reply_ready(self):
        r = await self._reply_q.get()
        self._reply_q.task_done()
        return r
