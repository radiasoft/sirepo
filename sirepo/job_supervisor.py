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
# TODO(e-carlin): Used to get is_parallel(). Should live in sim_data?
from sirepo import simulation_db
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

    async def do(self):
        self.handler.write(await _Job['_do_' + self.content.api](self))


def terminate():
    sirepo.driver.terminate()


class _Job(PKDict):
    instances = PKDict()

    def __init__(self, req):
        c = req.content
        super().__init__(
            is_parallel=simulation_db.is_parallel(PKDict(report=c.analysisModel)),
            jhash=c.computeJobHash,
            jid=c.computeJid,
            status=job.Status.MISSING.value,
            uid=c.uid,
        )
        if self.is_parallel:
            self.parallel_status = PKDict(
                frameCount=0,
                lastUpdateTime=0,
                percentComplete=0.0,
                startTime=0,
            )
        assert self.jid not in self.instances
        self.instances[self.jid] = self

    @classmethod
    async def get_instance(cls, req):
        return cls.instances.get(req.content.computeJid) or cls(req)

    @classmethod
    async def _do_api_runSimulation(cls, req):
        self = await _Job.get_instance(req)
        if self.status == job.Status.RUNNING.value:
            if self.jhash != req.content.computeJobHash:
                raise AssertionError('FIXME')
            return PKDict(state=job.Status.RUNNING.value)
        if (self.req.content.get('forceRun')
            or not (
                self.jhash == req.content.computeJobHash
                and self.status == job.Status.COMPLETED.value
            )
        ):
            self.status = job.Status.RUNNING.value
            self.error = None
            if self.is_parallel:
                t = time.time()
                self.parallel_status = PKDict(
                    frameCount=0,
                    lastUpdateTime=t,
                    percentComplete=0.0,
                    startTime=t,
                )
            return await self._run_op(job.OP_RUN, req)
        return PKDict(state=self.status)

    @classmethod
    async def _do_api_runStatus(cls, req):
        self = _Job.get_instance(req)

        def res(**kwargs):
            r = PKDict(**kwargs)
            if self.error:
                r.error = error
            if self.is_parallel:
                r.update(**self.parallel_status)
                r.elapsedTime = r.lastUpdateTime - r.startTime
            if self.status == job.Status.RUNNING.value:
                c = req.content
                r.update(
                    nextRequestSeconds=2 if r.is_parallel else 1,
                    nextRequest=PKDict(
                        report=c.analysisModel,
                        computeJobHash=self.compute_hash,
                        simulationId=c.simulationId,
                        simulationType=c.simulationType,
                    ),
                )
            return r

        if self.jhash != req.content.computeJobHash:
            return res(state=job.Status.MISSING.value)
        if self.is_parallel or self.status in (
            job.Status.ERROR.value,
            job.Status.CANCELED.value,
            job.Status.MISSING.value,
            job.Status.RUNNING.value,
        ):
            return res(state=self.status)
        assert self.res.state == job.Status.COMPLETED.value
        return await self._run_op(
            job.OP_ANALYSIS,
            req,
            'sequential_result',
        )

    @classmethod
    async def _do_api_simulationFrame(cls, req):
        self = _Job.get_instance(req)
        assert self.jhash == req.content.computeJobHash
        return await self._run_op(
            job.OP_ANALYSIS,
            req,
            'get_simulation_frame',
        )

    async def _run_op(self, op, req, jobProcessCmd=None):
        req.job = self
        return await sirepo.driver.do_op(
            self,
            req,
            op,
            jid=self.jid,
            jobProcessCmd=jobProcessCmd,
            **req.content,
        )

    def __repr__(self):
        return f'jid={self.jid} state={self.res.state} compute_hash={self.res.computeJobHash}'
