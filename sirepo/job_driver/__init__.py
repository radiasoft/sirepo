# -*- coding: utf-8 -*-
"""TODO(e-carlin): Doc

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkconfig, pkio, pkinspect, pkcollections, pkconfig, pkjson
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdlog, pkdc
from sirepo import job
from sirepo import job_supervisor, simulation_db
import importlib
import time
import tornado.ioloop
import tornado.locks
import tornado.queues


#: map of driver names to class
_CLASSES = None


#: default class when not determined by request
_DEFAULT_CLASS = None


cfg = None


async def send(req, kwargs):
    return await DriverBase.get_class(req).send(req, kwargs)


class AgentMsg(PKDict):

    async def receive(self):
        await DriverBase.receive(self)


class DriverBase(PKDict):
    driver_for_agents = PKDict()

    COMMUNICATING = 'communicating'
    IDLE = 'idle'
    KILLING = 'killing'
    STARTING = 'starting'

    def __init__(self, req):
        super().__init__(
            agentId=job.unique_key(),
            uid=req.content.uid,
        )
        self.driver_for_agents[self.agentId] = self

    def free(self):
        del self.driver_for_agents[self.agentId]

    @classmethod
    def get_class(cls, req):
        return _DEFAULT_CLASS

    @classmethod
    async def receive(cls, msg):
        self.driver_for_agents[msg.content.agentId]._receive(msg)

def init():
    global _CLASSES, _DEFAULT_CLASS, cfg
    assert not _CLASSES
    import types
    cfg = pkconfig.init(
        modules=(('local',), set, 'driver modules'),
        supervisor_uri=(
            'ws://{}:{}{}'.format(job.DEFAULT_IP, job.DEFAULT_PORT, job.AGENT_URI),
            str,
            'uri for agent ws connection with supervisor',
        ),
    )
    p = pkinspect.this_module().__name__
    _CLASSES = PKDict()
    for n in cfg.modules:
        m = importlib.import_module(pkinspect.module_name_join((p, n)))
        _CLASSES[n] = m.init_class()
    # when we support more than one class, we 'll have to define
    # _DEFAULT_CLASS some how
    assert len(_CLASSES) == 1
    _DEFAULT_CLASS = list(_CLASSES.values())[0]
