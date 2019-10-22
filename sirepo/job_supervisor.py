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
from sirepo import simulation_db # TODO(e-carlin): Used to get is_parallel(). Should live in sim_data?
import aenum
import copy
import sirepo.driver
import sirepo.job
import sys
import time
import tornado.locks


class AgentMsg(PKDict):

    async def do(self):
        pkdlog('content={}', self.content)
        if self.content.op == sirepo.job.OP_ERROR: # TODO(e-carlin): proper error handling
            raise AssertionError('TODO: Handle errors')
        d = sirepo.driver.get_instance_for_agent(self.content.agent_id)
        if not d:
            # TODO(e-carlin): handle
            pkdlog('no driver for agent_id={}', self.content.agent_id)
            return
        d.set_handler(self.handler)
        d.set_state(self.content)
        i = self.content.get('op_id')
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
        self.agent_dir = self.content.agent_dir
        self.compute_jid = self.content.compute_jid
        self.driver_kind = sirepo.driver.get_kind(self)
        self.run_dir = self.content.run_dir
        self.uid = self.content.uid
        # self._resource_class = sirepo.job
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
        raise AssertionError('api={} unkown', c.api)


def terminate():
    sirepo.driver.terminate()


class _Job(PKDict):
    instances = PKDict()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.jid = self._jid_for_req(self.req)
        self.instances[self.jid] = self
        self.background_percent_complete = None
        self.res = PKDict(
            state=None,
            computeJobHash=None,
            lastUpdateTime=time.time(),
            startTime=time.time(),
        )

    @classmethod
    async def get_compute_status(cls, req):
        #TODO(robnagler) deal with non-in-memory job state (db?)
        self = cls.instances.get(cls._jid_for_req(req))
        if not self:
            self = cls(req=req)
        self.req = req
        p = simulation_db.is_parallel(PKDict(report=req.content.analysis_model))
        if (p and self.background_percent_complete is not None) or \
            (not p and self.res.state is not None):
            return await self.get_response(req)
        d = await sirepo.driver.get_instance_for_job(self)
        # TODO(e-carlin): self.jid is not working properly. Ex. all api_runSimulation
        # requests come in and need to run status. They will use compute_jid even
        # though if they are a parallel sim the compute job runs under the compute_jid
        # but the analysis job needs to run under the analysis_jid
        if p:
            await d.do_op(
                op=sirepo.job.OP_ANALYSIS,
                jid=self.jid,
                job_process_cmd='background_percent_complete',
                is_running=self.res.state == sirepo.job.Status.RUNNING.value,
                **self.req.content,
            )
        else:
            # TODO(e-carlin): handle error response from do_op
            await d.do_op(
                op=sirepo.job.OP_COMPUTE_STATUS,
                jid=self.jid,
                **self.req.content,
            )
        return await self.get_response(req)

    def get_job_info(self, req):
        assert self.res.state is not None
        i = pkcollections.Dict(
            cached_hash=self.res.computeJobHash,
            state=self.res.state,
            model_name=req.content.compute_model,
            parameters_changed=False,
            req_hash=req.content.computeJobHash,
            simulation_id=req.content.data.simulationId,
            simulation_type=req.content.sim_type,
        )
        if self.res.state == sirepo.job.Status.MISSING.value:
            return i
        if i.req_hash == i.cached_hash:
            return i
        i.parameters_changed = True
        return i

    async def get_response(self, req):
        try:
            # TODO(e-carlin): This only works for compute_jobs now. What about analysis jobs?
            i = self.get_job_info(req)
            res = PKDict(state=i.state)
            # TODO(e-carlin):  Job is not processing then send result op
            if i.state in \
                (sirepo.job.Status.COMPLETED.value, sirepo.job.Status.ERROR.value) \
                and not i.parameters_changed:
                res = (await self.get_result(req)).output.result
            # TODO(e-carlin): handle parallel
            res.setdefault('parametersChanged', i.parameters_changed)
            res.setdefault('startTime', self.res.startTime)
            res.setdefault('lastUpdateTime', self.res.lastUpdateTime)
            res.setdefault('elapsedTime', res.lastUpdateTime - res.startTime)
            if self.background_percent_complete is not None:
                res.update(self.background_percent_complete)
            if self.res.state in (
                sirepo.job.Status.PENDING.value,
                sirepo.job.Status.RUNNING.value
                ):
                res.nextRequestSeconds = 2 # TODO(e-carlin): use logic from simulation_db.poll_seconds()
                res.nextRequest = PKDict(
                    report=i.model_name,
                    computeJobHash=i.cached_hash,
                    simulationId=i.simulation_id,
                    simulationType=i.simulation_type,
                )
        except Exception as e:
            pkdlog('error={} \n{}', e, pkdexc())
            return PKDict(error=e)
        return res

    @classmethod
    async def get_result(cls, req):
        self = cls.instances.get(cls._jid_for_req(req))
        if not self:
            self = cls(req=req)
        self.req = req
        d = await sirepo.driver.get_instance_for_job(self)
        # TODO(e-carlin): all other methods return self.get_response() this returns
        # the raw response. Is there a way to change this?
        return await d.do_op(
            op=sirepo.job.OP_RESULT,
            jid=self.req.compute_jid,
            **self.req.content,
        )

    @classmethod
    async def run(cls, req):
        # TODO(e-carlin): handle forceRun
        s = await _Job.get_compute_status(req)
        if s.state not in sirepo.job.ALREADY_GOOD_STATUS or s.parametersChanged:
            self = cls.instances.get(cls._jid_for_req(req))
            if not self:
                self = cls(req=req)
            self.req = req # if self then must overwrite existing req
            d = await sirepo.driver.get_instance_for_job(self)
            # TODO(e-carlin): handle error response from do_op
            self.res.startTime = time.time()
            self.res.lastUpdateTime = time.time()
            await d.do_op(
                op=sirepo.job.OP_RUN,
                jid=self.req.compute_jid,
                **self.req.content,
            )
        self = cls.instances.get(cls._jid_for_req(req))
        assert self is not None
        return await self.get_response(req)

    @classmethod
    def _jid_for_req(cls, req):
        """Get the jid (compute or analysis) for a job from a request.
        """
        c = req.content
        if c.api in ('api_runStatus', 'api_runCancel', 'api_runSimulation'):
            return c.compute_jid
        if c.api in ('api_simulationFrame',):
            return c.analysis_jid
        raise AssertionError('unknown api={} req={}', c.api, req)

    def __repr__(self):
        return f'jid={self.jid} state={self.res.state} compute_hash={self.res.computeJobHash}'