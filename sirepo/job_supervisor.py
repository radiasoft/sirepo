# -*- coding: utf-8 -*-
"""TODO(e-carlin): Doc

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkcollections
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdc, pkdlog, pkdexc
from sirepo import job
from sirepo import job_driver
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

def init():
    global _DB_DIR
    if _DB_DIR:
        return
    job.init()
    job_driver.init()
    _DB_DIR = sirepo.srdb.root().join(_DB_SUBDIR)
    pykern.pkio.mkdir_parent(_DB_DIR)


class ServerReq(PKDict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.uid = self.content.uid
        self._response = None
        self._response_received = tornado.locks.Event()

    async def receive(self):
        self.handler.write(await _ComputeJob.receive(self))


async def terminate():
    await job_driver.terminate()


class _ComputeJob(PKDict):

    instances = PKDict()

    def __init__(self, req, **kwargs):
        c = req.content
        super().__init__(_ops=[], **kwargs)
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
        return await getattr(
            cls.get_instance(req),
            '_receive_' + req.content.api,
        )(req)

    @classmethod
    def __create(cls, req):
        try:
            return cls(
                req,
                db=pkcollections.json_load_any(
                    cls.__db_file(req.content.computeJid),
                ),
            )
        except Exception as e:
            if pykern.pkio.exception_is_not_found(e):
                return cls(req).__db_write()
            raise

    @classmethod
    def __db_file(cls, computeJid):
        return _DB_DIR.join(computeJid + '.json')

    def __db_init(self, req):
        c = req.content
        self.db = PKDict(
            computeJid=c.computeJid,
            computeJobHash=c.computeJobHash,
            error=None,
            isParallel=c.isParallel,
            simulationId=c.simulationId,
            simulationType=c.simulationType,
#TODO(robnagler) when would req come in with status?
            status=req.get('status', job.MISSING),
            uid=c.uid,
        )
        if self.db.isParallel:
            self.db.parallelStatus = PKDict(
                elapsedTime=0,
                frameCount=0,
                lastUpdateTime=0,
                percentComplete=0.0,
                computeJobStart=0,
            )
        return self.db

    def __db_write(self):
        sirepo.util.json_dump(self.db, path=self.__db_file(self.db.computeJid))
        return self

    async def _receive_api_downloadDataFile(self, req):
        await self._send_with_single_reply(
            job.OP_ANALYSIS,
            req,
            jobProcessCmd='get_data_file'
        )

    async def _receive_api_runCancel(self, req):
        async def _reply_canceled(self, req):
            return PKDict(state=job.CANCELED)

        async def _cancel_queued(self, req):
            for o in self._ops:
                if o.msg.computeJid == req.content.computeJid:
                    o.set_canceled()
            return await _reply_canceled(self, req)

        async def _cancel_running(self, req):
            o = await self._send_with_single_reply(
                job.OP_CANCEL,
                req,
            )
            assert o.state == job.CANCELED
            return await _reply_canceled(self, req)

        if self.db.computeJobHash == req.content.computeJobHash:
            d = PKDict({
                job.CANCELED: _reply_canceled,
                job.COMPLETED: _reply_canceled,
                job.ERROR: _reply_canceled,
                job.MISSING: _reply_canceled,
                job.PENDING: _cancel_queued,
                job.RUNNING: _cancel_running,
            })
            r = d[self.db.status](self, req)
            self.db.status = job.CANCELED
            self.__db_write()
            return await r
        if self.db.computeJobHash != req.content.computeJobHash:
            self.db.status = job.CANCELED
            self.__db_write()
            return await _cancel_queued(self, req)

    async def _receive_api_runSimulation(self, req):
        if self.db.status == (job.RUNNING, job.PENDING):
            if self.db.computeJobHash != req.content.computeJobHash:
                raise AssertionError('FIXME')
            return PKDict(state=job.RUNNING)
        if (req.content.get('forceRun')
            or self.db.computeJobHash != req.content.computeJobHash
            or self.db.status != job.COMPLETED
        ):
            self.__db_init(req)
            self.db.status = job.PENDING
            if self.db.isParallel:
                t = time.time()
                self.db.parallelStatus.pkupdate(
                    computeJobStart=t,
                    lastUpdateTime=t,
                )
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
                r.update(**self.db.parallelStatus)
                r.elapsedTime = r.lastUpdateTime - r.computeJobStart
                r.computeJobHash = self.db.computeJobHash
            if self.db.status in (job.RUNNING, job.PENDING):
                c = req.content
                r.update(
                    nextRequestSeconds=2 if self.db.isParallel else 1,
                    nextRequest=PKDict(
                        report=c.analysisModel,
                        computeJobHash=self.db.computeJobHash,
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
            jobProcessCmd='sequential_result'
        )

    async def _receive_api_simulationFrame(self, req):
        assert self.db.computeJobHash == req.content.computeJobHash
        return await self._send_with_single_reply(
            job.OP_ANALYSIS, req,
            'get_simulation_frame'
        )

    async def _run(self, req):
        if self.db.computeJobHash != req.content.computeJobHash:
            pkdlog(
                'invalid computeJobHash self={} req={}',
                self.db.computeJobHash,
                req.content.computeJobHash
            )
            return
        o = await self._send(
            job.OP_RUN,
            req,
            jobProcessCmd='compute'
        )
        # TODO(e-carlin): XXX bug. If cancel comes in then self.db.status = canceled
        # This overwrites it, but there is a state=canceled message waiting for
        # us in the reply_ready q. We then await o.reply_ready() and get the cancel
        # message then set self.db.status back to canceled. This works because the
        # await o.reply_ready() doesn't block because there is a cancel message
        # in the q
        self.db.status = job.RUNNING
        self.__db_write()
        while True:
            r = await o.reply_ready()
            self.db.status = r.state
            if self.db.status == job.ERROR:
                self.db.error = r.get('error', '<unknown error>')
            if 'parallelStatus' in r:
                assert self.isParallel
                self.db.parallelStatus.update(r.parallelStatus)
                #TODO(robnagler) will need final frame count
            # TODO(e-carlin): What if this never comes?
            if 'opDone' in r:
                break
        self.destroy_op(o)
        self.__db_write()

    async def _send(self, opName, req, jobProcessCmd):
        # TODO(e-carlin): proper error handling
        try:
            req.kind = job.PARALLEL if self.db.isParallel and opName != job.OP_ANALYSIS \
                else job.SEQUENTIAL
            req.simulationType = self.db.simulationType
            # TODO(e-carlin): We need to be able to cancel requests waiting in this
            # state. Currently we assume that all requests get a driver and the
            # code does not block.
            d = await job_driver.get_instance(req)
            o = _Op(
                driver=d,
                msg=PKDict(
                    jobProcessCmd=jobProcessCmd,
                    **req.content,
                ),
                opName=opName,
            )
            self._ops.append(o)
            await d.send(o)
            return o
        except Exception as e:
            pkdlog('error={} stack={}', e , pkdexc())

    async def _send_with_single_reply(self, opName, req, jobProcessCmd=None):
        o = await self._send(opName, req, jobProcessCmd)
        r = await o.reply_ready()
        assert 'opDone' in r
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
        self.reply_put(PKDict(state=job.CANCELED, opDone=True))
        self.send_ready.set()
        self.driver.cancel_op(self)

    def set_errored(self, error):
        self.errored = True
        self.reply_put(
            PKDict(state=job.ERROR, error=error, opDone=True),
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
