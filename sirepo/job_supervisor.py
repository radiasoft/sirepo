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
import aenum
import copy
import sirepo.driver
import sirepo.job
import sys
import tornado.locks


_DATA_ACTIONS = (sirepo.job.ACTION_ANALYSIS, sirepo.job.ACTION_COMPUTE)

_OPERATOR_ACTIONS = (sirepo.job.ACTION_CANCEL,)

def init():
    sirepo.job.init()
    sirepo.driver.init()


def terminate():
    sirepo.driver.terminate()

class AgentMsg(PKDict):

    async def do(self):
        pkdlog('content={}', self.content)
        d = sirepo.driver.get_instance_for_agent(self.content.agent_id)
        if not d:
            # TODO(e-carlin): handle
            pkdlog('no driver for agent_id={}', self.content.agent_id)
            return
        d.set_handler(self.handler)
        i = self.content.get('op_id')
        if not i:
            # o = self.content.get()
            # TODO(e-carlin): op w/o id. Store the state in the job.
            return
        d.ops[i].set_result(self.content)


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
            # TODO(e-carlin): handle error from get_compute_status
            self.handler.write(await _Job.get_compute_status(self))
            return
        elif c.api == 'api_runSimulation':
            # TODO(e-carlin): handle error from get_compute_status
            s = await _Job.get_compute_status(self)
            if s not in sirepo.job.ALREADY_GOOD_STATUS:
                # TODO(e-carlin): Handle forceRun
                # TODO(e-carlin): Handle parametersChanged
                await _Job.run(self)
                self.handler.write({}) # TODO(e-carlin): What should be returned in response?
                return


        raise AssertionError('api={} unkown', c.api)


class _RequestState(aenum.Enum):
    CHECK_STATUS = 'check_status'
    REPLY = 'reply'
    RUN = 'run'
    RUN_PENDING = 'run_pending'


class _Job(PKDict):
    instances = PKDict()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.jid = self._jid_for_req(self.req)
        # self.agent_dir = self.req.content.agent_dir
        # self.driver_kind = self.req.driver_kind
        # self.run_dir = self.req.content.run_dir
        # self.uid = self.req.content.uid
        self.instances[self.jid] = self

    @classmethod
    async def get_compute_status(cls, req):
        """Get the status of a compute job.
        """
        #TODO(robnagler) deal with non-in-memory job state (db?)
        self = cls.instances.get(cls._jid_for_req(req))
        if not self:
            self = cls(req=req)
        d = await sirepo.driver.get_instance_for_job(self)
        # TODO(e-carlin): handle error response from do_op
        r = await d.do_op(
            op=sirepo.job.OP_COMPUTE_STATUS,
            jid=self.req.compute_jid,
            run_dir=self.req.run_dir,
        )
        r.status = r.compute_status
        return r

    @classmethod
    async def run(cls, req):
        self = cls.instances.get(cls._jid_for_req(req))
        if not self:
            self = cls(req=req)
        d = await sirepo.driver.get_instance_for_job(self)
        # TODO(e-carlin): handle error response from do_op
        r = await d.do_op(
            op=sirepo.job.OP_RUN,
            jid=self.req.compute_jid,
            **self.req.content,
        )
        return r

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
