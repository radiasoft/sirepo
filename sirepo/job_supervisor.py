# -*- coding: utf-8 -*-
"""TODO(e-carlin): Doc

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdc, pkdlog, pkdexc
from sirepo import job
from sirepo import job_driver
import aenum
import collections
import copy
import os
import pykern.pkio
import sirepo.srdb
import sirepo.util
import sys
import time
import tornado.gen
import tornado.ioloop
import tornado.locks


#: we job files are stored
_LIB_FILE_DIR = None

#: where job_processes request files
_LIB_FILE_URI = None

#: where job_process will PUT data files
_DATA_FILE_URI = None


def init():
    global _LIB_FILE_DIR, _LIB_FILE_URI, _DATA_FILE_URI

    assert not _LIB_FILE_DIR
    job.init()
    job_driver.init()
    s = sirepo.srdb.root().join(job.LIB_FILE_DIR)
    pykern.pkio.unchecked_remove(s)
    _LIB_FILE_DIR = s.join(job.LIB_FILE_URI)
    pykern.pkio.mkdir_parent(_LIB_FILE_DIR)
    _LIB_FILE_URI = job.cfg.supervisor_uri + job.LIB_FILE_URI + '/'
    _DATA_FILE_URI = job.cfg.supervisor_uri + job.DATA_FILE_URI
    return s


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

    def __init__(self, req):
        c = req.content
        super().__init__(
            computeJid=c.computeJid,
            computeJobHash=c.computeJobHash,
            error=None,
            isParallel=c.isParallel,
            simulationId=c.data.get('simulationId') or c.data.models.simulation.simulationId,
            simulationType=c.data.simulationType,
            status=job.MISSING,
            uid=c.uid,
            _ops=[]
        )
        if self.isParallel:
            self.parallelStatus = PKDict(
                elapsedTime=0,
                frameCount=0,
                lastUpdateTime=0,
                percentComplete=0.0,
                startTime=0,
            )
        assert self.computeJid not in self.instances
        self.instances[self.computeJid] = self

    def destroy_op(self, op):
        self._lib_file_link_destroy()
        self._ops.remove(op)
        op.destroy()

    @classmethod
    async def receive(cls, req):
        return await getattr(
            cls.instances.get(req.content.computeJid) or cls(req),
            '_receive_' + req.content.api,
        )(req)


    def _lib_file_uri(self, libDir):
        self.libFileLink = l = _LIB_FILE_DIR.join(job.unique_key())
        sirepo.util.dump_json(
            [x.basename for x in libDir.listdir()],
            path=libDir.join(job.LIB_FILE_LIST_URI),
        )
        os.symlink(l.dirpath().bestrelpath(libDir), l)
        return _LIB_FILE_URI + l.basename

    def _lib_file_link_destroy(self):
        d = self.pkdel('libFileLink')
        if d:
            d.remove(rec=False, ignore_errors=True)

    async def _receive_api_downloadDataFile(self, req):
        req.content.dataFileUri = _DATA_FILE_URI
        await self._send_with_single_reply(
            job.OP_ANALYSIS,
            req,
            jobProcessCmd='get_data_file'
        )
        d = pykern.pkio.py_path(req.content.tmpDir).listdir()
        assert len(d) == 1, '{}: should only be one file in dir'.format(d)
        return PKDict(file=d[0].basename)

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

        if self.computeJobHash == req.content.computeJobHash:
            d = PKDict({
                job.CANCELED: _reply_canceled,
                job.COMPLETED: _reply_canceled,
                job.ERROR: _reply_canceled,
                job.MISSING: _reply_canceled,
                job.PENDING: _cancel_queued,
                job.RUNNING: _cancel_running,
            })
            r = d[self.status](self, req)
            self.status = job.CANCELED
            return await r
        if self.computeJobHash != req.content.computeJobHash:
            self.status = job.CANCELED
            return await _cancel_queued(self, req)

    async def _receive_api_runSimulation(self, req):
        if self.status == (job.RUNNING, job.PENDING):
            if self.computeJobHash != req.content.computeJobHash:
                raise AssertionError('FIXME')
            return PKDict(state=job.RUNNING)
        if (req.content.get('forceRun')
            or self.computeJobHash != req.content.computeJobHash
            or self.status != job.COMPLETED
        ):
            self.computeJobHash = req.content.computeJobHash
            self.isParralel = req.content.isParallel
            self.parallelStatus = None
            self.error = None
            self.status = job.PENDING
            if self.isParallel:
                t = time.time()
                self.parallelStatus = PKDict(
                    frameCount=0,
                    lastUpdateTime=t,
                    percentComplete=0.0,
                    startTime=t,
                )
            tornado.ioloop.IOLoop.current().add_callback(self._run, req)
        # Read this first https://github.com/radiasoft/sirepo/issues/2007
        return await self._receive_api_runStatus(req)

    async def _receive_api_runStatus(self, req):
        def res(**kwargs):
            r = PKDict(**kwargs)
            if self.error:
                r.error = self.error
            if self.isParallel:
                r.update(**self.parallelStatus)
                r.elapsedTime = r.lastUpdateTime - r.startTime
            if self.status in (job.RUNNING, job.PENDING):
                c = req.content
                r.update(
                    nextRequestSeconds=2 if self.isParallel else 1,
                    nextRequest=PKDict(
                        report=c.analysisModel,
                        computeJobHash=self.computeJobHash,
                        simulationId=self.simulationId,
                        simulationType=self.simulationType,
                    ),
                )
            return r
        if self.computeJobHash != req.content.computeJobHash:
            return res(state=job.MISSING)
        if self.isParallel or self.status != job.COMPLETED:
            return res(state=self.status)
        return await self._send_with_single_reply(
            job.OP_ANALYSIS,
            req,
            jobProcessCmd='sequential_result'
        )

    async def _receive_api_simulationFrame(self, req):
        assert self.computeJobHash == req.content.computeJobHash
        return await self._send_with_single_reply(
            job.OP_ANALYSIS, req,
            'get_simulation_frame'
        )

    async def _run(self, req):
        if self.computeJobHash != req.content.computeJobHash:
            pkdlog(
                'invalid computeJobHash self={} req={}',
                self.computeJobHash,
                req.content.computeJobHash
            )
            return
        req.content.libFileUri = self._lib_file_uri(
            pykern.pkio.py_path(req.content.libDir),
        )
        o = await self._send(
            job.OP_RUN,
            req,
            jobProcessCmd='compute'
        )
        # TODO(e-carlin): XXX bug. If cancel comes in then self.status = canceled
        # This overwrites it, but there is a state=canceled message waiting for
        # us in the reply_ready q. We then await o.reply_ready() and get the cancel
        # message then set self.status back to canceled. This works because the
        # await o.reply_ready() doesn't block because there is a cancel message
        # in the q
        self.status = job.RUNNING
        while True:
            r = await o.reply_ready()
            self.status = r.state
            if self.status == job.ERROR:
                self.error = r.get('error', '<unknown error>')
            if 'parallelStatus' in r:
                assert self.isParralel
                self.parallelStatus.update(r.parallelStatus)
                #TODO(robnagler) will need final frame count
            # TODO(e-carlin): What if this never comes?
            if 'opDone' in r:
                break
        self.destroy_op(o)

    async def _send(self, opName, req, jobProcessCmd):
        # TODO(e-carlin): proper error handling
        try:
            req.kind = job.PARALLEL if self.isParallel and opName != job.OP_ANALYSIS \
                else job.SEQUENTIAL
            req.simulationType = self.simulationType
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
