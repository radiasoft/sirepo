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
import tornado.locks


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
            isParallel=c.isParallel,
            status=job.MISSING,
            uid=c.uid,
        )
        if self.isParallel:
            self.parallelStatus = PKDict(
                frameCount=0,
                lastUpdateTime=0,
                percentComplete=0.0,
                startTime=0,
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
        if self.status == job.RUNNING:
            if self.computeJobHash != req.content.computeJobHash:
                raise AssertionError('FIXME')
            return PKDict(state=job.RUNNING)
        if not (self.req.content.get('forceRun')
            or not (
                self.computeJobHash == req.content.computeJobHash
                and self.status == job.COMPLETED
            )
        ):
            return PKDict(state=self.status)
        self.status = job.RUNNING
        self.error = None
        if self.isParallel:
            t = time.time()
            self.parallelStatus = PKDict(
                frameCount=0,
                lastUpdateTime=t,
                percentComplete=0.0,
                startTime=t,
            )
        return await self._send(job.OP_RUN, req)

    async def _receive_api_runStatus(self, req):
        def res(**kwargs):
            r = PKDict(**kwargs)
            if self.error:
                r.error = error
            if self.isParallel:
                r.update(**self.parallelStatus)
                r.elapsedTime = r.lastUpdateTime - r.startTime
            if self.status == job.RUNNING:
                c = req.content
                r.update(
                    nextRequestSeconds=2 if r.isParallel else 1,
                    nextRequest=PKDict(
                        report=c.analysisModel,
                        computeJobHash=self.compute_hash,
                        simulationId=c.simulationId,
                        simulationType=c.simulationType,
                    ),
                )
            return r

        if self.computeJobHash != req.content.computeJobHash:
            return res(state=job.MISSING)
        if self.isParallel or self.status != job.COMPLETED:
            return res(state=self.status)
        return await self._send(job.OP_ANALYSIS, req, 'sequential_result')

    async def _receive_api_simulationFrame(self, req):
        assert self.computeJobHash == req.content.computeJobHash
        return await self._send(job.OP_ANALYSIS, req, 'get_simulation_frame')

    async def _send(self, opName, req, jobProcessCmd=None):
        req.kind = job.PARALLEL if self.isParallel and opName != job.OP_ANALYSIS \
            else job.SEQUENTIAL
        return await job_driver.send(
            req,
            PKDict(
                computeJid=self.computeJid,
                reqKind=req.kind,
                jobProcessCmd=jobProcessCmd,
                opName=opName,
                **req.content,
            ),
        )
