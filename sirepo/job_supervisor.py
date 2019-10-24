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
# TODO(e-carlin): Used to get is_parallel(). Should live in sim_data?
from sirepo import simulation_db
import aenum
import copy
import sirepo.driver
import sirepo.job
import sys
import time
import tornado.locks


class AgentMsg(PKDict):

    async def do(self):
        pkdlog('content={}', sirepo.job.LogFormatter(self.content))
        # TODO(e-carlin): proper error handling
        if self.content.op == sirepo.job.OP_ERROR:
            raise AssertionError('TODO: Handle errors')
        d = sirepo.driver.get_instance_for_agent(self.content.agentId)
        if not d:
            # TODO(e-carlin): handle
            pkdlog('no driver for agent_id={}', self.content.agentId)
            return
        d.set_handler(self.handler)
        d.set_state(self.content)
        i = self.content.get('opId')
        if not i:
            return
        d.ops[i].set_result(self.content)


def init():
    sirepo.job.init()
    sirepo.driver.init()


class Op(PKDict):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._result_set = tornado.locks.Event()
        self._result = None

    async def get_result(self):
        await self._result_set.wait()
        return self._result

    def set_result(self, res):
        self._result = res
        self._result_set.set()


class ServerReq(PKDict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.agent_dir = self.content.agentDir
        self.driver_kind = sirepo.driver.get_kind(self)
        self.uid = self.content.uid
        self._response = None
        self._response_received = tornado.locks.Event()

    async def do(self):
        c = self.content
        if c.api == 'api_runStatus':
            self.handler.write(await _Job.get_compute_status(self))
            return
        elif c.api == 'api_runSimulation':
            self.handler.write(await _Job.run(self))
            return
        elif c.api == 'api_simulationFrame':
            self.handler.write(await _Job.get_simulation_frame(self))
            return
        raise AssertionError('api={} unkown', c.api)


def terminate():
    sirepo.driver.terminate()


class _Job(PKDict):
    instances = PKDict()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.jid = self._jid_for_req(self.req)
        self.instances[self.jid] = self
        self.res = PKDict(
            backgroundPercentComplete=PKDict(
                percentComplete=0.0,
                frameCount=0,
            ),
            computeJobHash=None,
            lastUpdateTime=None,
            startTime=None,
            state=None,
        )
        self._analysis_lock = tornado.locks.Lock()
        self._req_lock = tornado.locks.Lock()

    @classmethod
    async def get_instance(cls, req):
        """Get a job instance and determine if the computJobHash is same as the req.

        Args:
            req: The incoming request

        Returns:
            tuple: an instance of a job, True if the req computeJobashHash is
            the same as the computeJobHash of the job instance
        """
        # TODO(robnagler) deal with non-in-memory job state (db?)
        self = cls.instances.get(cls._jid_for_req(req))
        if not self:
            # we don't have any record of a compute job with the req jid
            self = cls(req=req)
            await self._req_lock.acquire()
            # populate it's initial state
            d = await sirepo.driver.get_instance_for_job(self)
            o = await d.do_op(
                op=sirepo.job.OP_COMPUTE_STATUS,
                jid=self.jid,
                **self.req.content,
            )
            await o.get_result()
            if self.res.computeJobHash == req.content.computeJobHash:
                # computeJob on disk is same as req
                return self, True
            if self.res.state == sirepo.job.Status.MISSING.value \
                    and self.res.computeJobHash is None:
                # no computeJob on disk so req can be valid by default
                self.res.computeJobHash = req.content.computeJobHash
                return self, True
            # computeJob on disk has different hash than req
            return self, False
        # we have an in memory (and thus on disk) record of a computeJob with the req jid
        await self._req_lock.acquire()
        if self.res.computeJobHash == req.content.computeJobHash:
            # computeJob in memory (and thus on disk) hash same hash as req
            return self, True
        assert self.res.computeJobHash is not None
        # computeJob in memory (and thus on disk) has different hash than req
        return self, False

    @classmethod
    async def run(cls, req):
        self, same_hash = await _Job.get_instance(req)
        if self.res.state == sirepo.job.Status.RUNNING.value:
            # TODO(e-carlin): Maybe we cancel the job and start the new one?
            self._req_lock.release()
            raise RuntimeError(
                'must issue cancel before sim with jid={} can be run'.format(
                    cls._jid_for_req(req))
            )
        # TODO(e-carlin): handle forceRun
        if not same_hash or self.res.state in (
            sirepo.job.Status.MISSING.value,
            sirepo.job.Status.CANCELED.value):
            # What on disk is old or there is nothing on disk
            d = await sirepo.driver.get_instance_for_job(self)
            # TODO(e-carlin): handle error response from do_op
            self.res.startTime = time.time()
            self.res.lastUpdateTime = time.time()
            self.res.state = sirepo.job.Status.RUNNING.value
            self.res.computeJobHash = self.req.content.computeJobHash
            d = await sirepo.driver.get_instance_for_job(self)
            # OP_RUN is "fast" so don't release self._req_lock().
            # In addition self._get_result() below expects it to be held.
            o = await d.do_op(
                op=sirepo.job.OP_RUN,
                jid=self.jid,
                **self.req.content,
            )
            await o.get_result()
        return await self._get_result(req)

    @classmethod
    async def get_compute_status(cls, req):
        self, same_hash = await _Job.get_instance(req)
        if not same_hash:
            self._req_lock.release()
            return PKDict(state=sirepo.job.Status.MISSING.value)

        return await self._get_result(req)

    async def _get_result(self, req):
        if self.res.state == sirepo.job.Status.ERROR.value:
            self._req_lock.release()
            # TODO(e-carlin): make sure there is self.res.error
            return PKDict(state=self.res.state, error=self.res.error)
        if self.res.state == sirepo.job.Status.CANCELED.value \
                or self.res.state == sirepo.job.Status.MISSING.value:
            self._req_lock.release()
            return PKDict(state=self.res.state)
        if self.res.state == sirepo.job.Status.RUNNING.value:
            res = PKDict(state=self.res.state)
            # TODO(e-carlin): simulation_db.poll_seconds()
            res.nextRequestSeconds = 2
            res.nextRequest = PKDict(
                report=req.content.computeModel,
                computeJobHash=self.res.computeJobHash,
                simulationId=self.req.content.data.simulationId,
                simulationType=req.content.simType,
            )
            # TODO(e-carlin): is res.report right? analysisModel?
            if simulation_db.is_parallel(PKDict(report=res.nextRequest.report)):
                n = self.res.backgroundPercentComplete
                n.setdefault('percentComplete', 0.0)
                n.setdefault('frameCount', 0)
                res.update(n)
            self._req_lock.release()
            return res

        if self.res.state == sirepo.job.Status.COMPLETED.value:
            if simulation_db.is_parallel(PKDict(report=req.content.computeModel)):
                self._req_lock.release()
                return PKDict(state=self.res.state)
            async with self._analysis_lock:
                d = await sirepo.driver.get_instance_for_job(self)
                o = await d.do_op(
                    op=sirepo.job.OP_RESULT,
                    jid=self.jid,
                    **self.req.content,
                )
                self._req_lock.release()
                r = await o.get_result()
                return PKDict(
                    **r.output.result,
                )
        raise AssertionError('state={} unrecognized'.format(self.res.state))

    def update_state(self, state):
        # TODO(e-carlin): only some state should be updated
        self.res.update(**state)

    # def get_job_info(self, req):
    #     i = pkcollections.Dict(
    #         cached_hash=self.res.computeJobHash,
    #         state=self.res.state,
    #         model_name=req.content.compute_model,
    #         parameters_changed=False,
    #         req_hash=req.content.computeJobHash,
    #         simulation_id=req.content.data.simulationId,
    #         simulation_type=req.content.sim_type,
    #     )
    #     if i.req_hash != i.cached_hash:
    #         i.parameters_changed = True
    #     return i

    # def get_response(self, req):
    #     try:
    #         # TODO(e-carlin): This only works for compute_jobs now. What about analysis jobs?
    #         i = self.get_job_info(req)
    #         res = PKDict(state=i.state)
    #         res.update(self.res)
    #         # # TODO(e-carlin):  Job is not processing then send result op
    #         res.setdefault('parametersChanged', i.parameters_changed)
    #         res.setdefault('startTime', self.res.startTime)
    #         res.setdefault('lastUpdateTime', self.res.lastUpdateTime)
    #         res.setdefault('elapsedTime', res.lastUpdateTime - res.startTime)
    #         if self.res.state in (
    #             sirepo.job.Status.PENDING.value,
    #             sirepo.job.Status.RUNNING.value
    #         ):
    #             # TODO(e-carlin): use logic from simulation_db.poll_seconds()
    #             res.nextRequestSeconds = 2
    #             res.nextRequest = PKDict(
    #                 report=i.model_name,
    #                 computeJobHash=i.cached_hash,
    #                 simulationId=i.simulation_id,
    #                 simulationType=i.simulation_type,
    #             )
    #     except Exception as e:
    #         pkdlog('error={} \n{}', e, pkdexc())
    #         return PKDict(error=e)
    #     self.res.update(res)
    #     return res

    # @classmethod
    # async def get_simulation_frame(cls, req):
    #     self = cls.instances.get(cls._jid_for_req(req))
    #     if not self:
    #         self = cls(req=req)
    #     # TODO(e-carlin): Doing the could cause some confusion if the GUI was
    #     # ever send multiple requests concurrently regarding the same jid. One
    #     # req would wipe out the other req.
    #     self.req = req
    #     d = await sirepo.driver.get_instance_for_job(self)
    #     await d.do_op(
    #         op=sirepo.job.OP_ANALYSIS,
    #         jid=self.jid,
    #         job_process_cmd='get_simulation_frame',
    #         **self.req.content,
    #     )
    #     return self.get_response(req)

    @classmethod
    def _jid_for_req(cls, req):
        """Get the jid (compute or analysis) for a job from a request.
        """
        c = req.content
        if c.api in ('api_runStatus', 'api_runCancel', 'api_runSimulation'):
            return c.computeJid
        if c.api in ('api_simulationFrame',):
            return c.analysisJid
        raise AssertionError('unknown api={} req={}', c.api, req)

    def __repr__(self):
        return f'jid={self.jid} state={self.res.state} compute_hash={self.res.computeJobHash}'
