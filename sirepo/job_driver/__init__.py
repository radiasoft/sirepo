# -*- coding: utf-8 -*-
"""Base for drivers

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkconfig, pkio, pkinspect, pkcollections, pkconfig, pkjson
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdlog, pkdc
from sirepo import job
import importlib


#: map of driver names to class
_CLASSES = None

#: default class when not determined by request
_DEFAULT_CLASS = None

cfg = None


class AgentMsg(PKDict):

    async def receive(self):
        # Agent messages do not block the supervisor
        DriverBase.receive(self)


class DriverBase(PKDict):
    agents = PKDict()

    def __init__(self, req):
        super().__init__(
            agentId=job.unique_key(),
            ops=PKDict(),
            supervisor_uri=cfg.supervisor_uri,
            uid=req.content.uid,
        )
        self.agents[self.agentId] = self

    @classmethod
    def receive(cls, msg):
        self.agents[msg.content.agentId]._receive(msg)

    def websocket_on_close(self):
        self.websocket_free()

    def _free(self):
        self._websocket_free()
        del self.agents[self.agentId]

    @classmethod
    def _kind(cls, req, kwargs):
        if req.computeJob.isParallel and kwargs.opName != job.OP_ANALYSIS:
            return job.PARALLEL
        return job.SEQUENTIAL

    def _op_send(self, req, kwargs):
        o = _Op(opName=kwargs.opName, msg=PKDict(kwargs))
        self.ops[o.opId] = o
        return await o.send(self)

    def _receive(self, msg):
        c = msg.content
        i = c.get('opId')
#rn there are two cases here in receive:
#  a "real" receive (unsolicited op) or a reply.
        if i:
            o = self.ops[i]
            del self.ops[i]
            o.reply(msg.reply)
        else:
            getattr(self, '_receive_' + c.opName)(msg)

    def _receive_alive(self, msg):
        """Receive an ALIVE message from our agent

        Save the websocket and register self with the websocket
        """
        if self.get('websocket', msg.handler) == msg.handler:
            return
        self._websocket_free()
        self.websocket = msg.handler
        self.websocket.sr_driver_set(self)

    def _websocket_free(self):
        w = self.get('websocket')
        if w:
            del self['websocket']
            # May be irrelevant, but need to call in some cases
            w.close()
        v = list(self.ops.values())
        self.ops.clear()
        for o in v:
            o.reply(PKDict(state=job.ERROR, error='websocket closed'))
#TODO(robnagler) for the local driver, we might want to kill the process (SIGKILL),
#   because there would be no reason for the websocket to disappear on its own.


async def send(req, kwargs):
    return await _DEFAULT_CLASS.send(req, kwargs)


def init():
    global _CLASSES, _DEFAULT_CLASS, cfg
    assert not _CLASSES

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
    assert len(_CLASSES) == 1
    _DEFAULT_CLASS = list(_CLASSES.values())[0]


class _Op(PKDict):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.opId = job.unique_key()
        self.msg.update(opId=self.opId, opName=self.opName)

    def reply(self, msg):
        self.reply_q.put_nowait(msg)

    async def send(self, driver):
        driver.write_message(pkjson.dump_bytes(self.msg))
        q = self.reply_q = tornado.queues.Queue()
        return await q.get()
