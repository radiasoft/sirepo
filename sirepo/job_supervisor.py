# -*- coding: utf-8 -*-
"""TODO(e-carlin): Doc

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkcollections
from pykern import pkjson
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdc, pkdlog, pkdexc
from sirepo import job
from sirepo import job_driver
import aenum
import copy
import sys
import time
import tornado.ioloop
import tornado.locks
import tornado.gen


def init():
    job.init()
    job_driver.init()


class ServerReq(PKDict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.uid = self.content.uid
        self._response = None
        self._response_received = tornado.locks.Event()

    async def receive(self):
        self.handler.write(await _ComputeJob.receive(self))


def terminate():
    job_driver.terminate()


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
        )
        if self.isParallel:
            self.parallelStatus = PKDict(
                frameCount=0,
                percentComplete=0.0,
                lastUpdateTime=0,
                startTime=0,
                elapsedTime=0,
            )
        assert self.computeJid not in self.instances
        self.instances[self.computeJid] = self

    @classmethod
    async def receive(cls, req):
        return await getattr(
            cls.instances.get(req.content.computeJid) or cls(req),
            '_receive_' + req.content.api,
        )(req)

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
        o = await self._send(
            job.OP_RUN, req,
            jobProcessCmd='compute'
        )
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
        o.close()

    async def _send_with_single_reply(self, opName, req, jobProcessCmd=None):
        o = await self._send(opName, req, jobProcessCmd)
        r = await o.reply_ready()
        assert 'opDone' in r
        o.close()
        return r

    async def _send(self, opName, req, jobProcessCmd):
        req.kind = job.PARALLEL if self.isParallel and opName != job.OP_ANALYSIS \
            else job.SEQUENTIAL
        req.simulationType = self.simulationType
        return await job_driver.send(
            req,
            PKDict(
                reqKind=req.kind,
                jobProcessCmd=jobProcessCmd,
                opName=opName,
                **req.content,
            ),
        )