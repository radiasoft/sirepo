# -*- coding: utf-8 -*-
"""Base for drivers

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkconfig, pkio, pkinspect, pkcollections, pkconfig, pkjson
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdlog, pkdc, pkdexc
from sirepo import job
import collections
import importlib
import tornado.gen
import tornado.ioloop
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
            has_slot=False,
            has_ws=False,
            ops_pending_done=PKDict(),
            ops_pending_send=[],
            uid=req.content.uid,
            _agentId=job.unique_key(),
            _supervisor_uri=cfg.supervisor_uri,
            _websocket=None,
        )
        self.agents[self._agentId] = self

    def cancel_op(self, op):
        for o in self.ops_pending_send:
            if o == op:
                self.ops_pending_send.remove(o)
        for o in self.ops_pending_done.copy().values():
            if o == op:
                del self.ops_pending_done[o.opId]

    def destroy_op(self, op):
        assert op not in self.ops_pending_send
        # canceled ops are removed in self.cancel_op()
        if not op.canceled:
            del self.ops_pending_done[op.opId]
        self.run_scheduler(self._kind)

    @classmethod
    def receive(cls, msg):
        cls.agents[msg.content.agentId]._receive(msg)

    async def send(self, op):
#TODO(robnagler) need to send a retry to the ops, which should requeue
#  themselves at an outer level(?).
#  If a job is still running, but we just lost the websocket, want to
#  pickup where we left off. If the op already was written, then you
#  have to ask the agent. If ops are idempotent, we can simply
#  resend the request. If it is in process, then it will be reconnected
#  to the job. If it was already completed (and reply on the way), then
#  we can cache that state in the agent(?) and have it send the response
#  twice(?).
        self.ops_pending_send.append(op)
        self.run_scheduler(self._kind)
        await op.send_ready.wait()
        if op.opId in self.ops_pending_done:
            self._websocket.write_message(pkjson.dump_bytes(op.msg))
        else:
            pkdlog('canceled op={}', op)
        assert op not in self.ops_pending_send

    @classmethod
    def terminate(cls):
        for d in DriverBase.agents.values():
            d.kill()

    def websocket_on_close(self):
        self._websocket_free()

    def _free(self):
        del self.agents[self._agentId]
        self._websocket_free()

    def _receive(self, msg):
        c = msg.content
        i = c.get('opId')
        if i:
            self.ops_pending_done[i].reply_put(c.reply)
        else:
            getattr(self, '_receive_' + c.opName)(msg)

    def _receive_alive(self, msg):
        """Receive an ALIVE message from our agent

        Save the websocket and register self with the websocket
        """
        if self._websocket:
            if self._websocket == msg.handler:
                return
            self._websocket_free()
        self._websocket = msg.handler
        self._websocket.sr_driver_set(self)
        self.has_ws = True
        self.run_scheduler(self._kind)

    def _websocket_free(self):
        w = self._websocket
        self._websockt = None
        if w:
            # Will not call websocket_on_close()
            w.sr_close()
        t = list(
            self.ops_pending_done.values()
            ).extend(self.ops_pending_send)
        self.has_ws = False
        self.ops_pending_done.clear()
        self.ops_pending_send = []
        for o in t:
            o.send_ready.set()
            o.reply_put(
                PKDict(state=job.ERROR, error='websocket closed', opDone=True),
            )
        self.run_scheduler(self._kind)


async def get_instance(req):
    return await _DEFAULT_CLASS.get_instance(req)


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


def terminate():
    DriverBase.terminate()


