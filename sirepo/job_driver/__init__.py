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
import tornado.locks


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
            _websocket_ready=tornado.locks.Event(),
        )
        self.agents[self.agentId] = self

    @classmethod
    def receive(cls, msg):
        cls.agents[msg.content.agentId]._receive(msg)

    async def _send(self, req, kwargs):
        await self._websocket_ready.wait()
        o = _Op(
            opName=kwargs.opName,
            msg=PKDict(kwargs).pkupdate(simulationType=req.simulationType),
        )
        self.ops[o.opId] = o
        self._websocket.write_message(pkjson.dump_bytes(o.msg))
        return await o.reply_ready()

    @classmethod
    def terminate(cls):
        for d in DriverBase.agents.values():
            d.kill()

    def websocket_on_close(self):
        self._websocket_free()

    def _free(self):
        del self.agents[self.agentId]
        self._websocket_free()

    def _receive(self, msg):
        c = msg.content
        i = c.get('opId')
#rn there are two cases here in receive:
#  a "real" receive (unsolicited op) or a reply.
        if i:
            self.ops.pkdel(i).reply_put(c.reply)
        else:
            getattr(self, '_receive_' + c.opName)(msg)

    def _receive_alive(self, msg):
        """Receive an ALIVE message from our agent

        Save the websocket and register self with the websocket
        """
        s = self.get('_websocket')
        if s:
            if s == msg.handler:
                return
            self._websocket_free()
        self._websocket = msg.handler
        self._websocket.sr_driver_set(self)
        self._websocket_ready.set()

    def _websocket_free(self):
        self._websocket_ready.clear()
        w = self.pkdel('_websocket')
        if w:
            # Will not call websocket_on_close()
            w.sr_close()
        v = list(self.ops.values())
        self.ops.clear()
        for o in v:
            o.reply_put(PKDict(state=job.ERROR, error='websocket closed'))


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


async def send(req, kwargs):
    return await _DEFAULT_CLASS.send(req, kwargs)


def terminate():
    DriverBase.terminate()


class _Op(PKDict):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.update(
            opId=job.unique_key(),
            _reply_q=tornado.queues.Queue(),
        )
        self.msg.update(opId=self.opId, opName=self.opName)

    def reply_put(self, msg):
        self._reply_q.put_nowait(msg)

    async def reply_ready(self):
        return await self._reply_q.get()
