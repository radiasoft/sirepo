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
import sirepo.srdb


KILL_TIMEOUT_SECS = 3

#: map of driver names to class
_CLASSES = None

#: default class when not determined by request
_DEFAULT_CLASS = None


class AgentMsg(PKDict):

    async def receive(self):
        # Agent messages do not block the supervisor
        DriverBase.receive(self)


class DriverBase(PKDict):

    agents = PKDict()

    def __init__(self, req):
        super().__init__(
            _agentId=job.unique_key(),
            has_slot=False,
            kind=req.kind,
            ops_pending_done=PKDict(),
            ops_pending_send=[],
            uid=req.content.uid,
            websocket=None,
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
        if not op.canceled and not op.errored:
            del self.ops_pending_done[op.opId]
        self.run_scheduler(self)

    def get_ops_pending_done_types(self):
        d = collections.defaultdict(int)
        for v in self.ops_pending_done.values():
            d[v.msg.opName] += 1
        return d

    def get_ops_with_send_allocation(self):
        """Get ops that could be sent assuming outside requirements are met.
        Outside requirements are an alive websocket connection and the driver
        having a slot.
        """
        r = []
        t = self.get_ops_pending_done_types()
        for o in self.ops_pending_send:
            if (o.msg.opName in t
                and t[o.msg.opName] > 0
            ):
                continue
            assert o.opId not in self.ops_pending_done
            t[o.msg.opName] += 1
            r.append(o)
        return r

    @classmethod
    def init_class(cls):
# TODO(e-carlin): this is not right for sbatch driver. No kinds
        for k in job.KINDS:
            cls.instances[k] = []
        return cls

    @classmethod
    def receive(cls, msg):
        try:
            cls.agents[msg.content.agentId]._receive(msg)
        except KeyError as e:
            pkdc('unknown agent msg={}', msg)
            try:
                msg.handler.write_message(PKDict(opName=job.OP_KILL))
            except Exception as e:
                pkdlog('error={} stack={}', e, pkdexc())

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
        self.run_scheduler(self)
        await op.send_ready.wait()
        if op.opId in self.ops_pending_done:
            self.websocket.write_message(pkjson.dump_bytes(op.msg))
        else:
            pkdlog('canceled op={}', job.LogFormatter(op))
        assert op not in self.ops_pending_send

    @classmethod
    async def terminate(cls):
        for d in DriverBase.agents.copy().values():
            try:
                await d.kill()
            except Exception as e:
                # If one kill fails still try to kill the rest
                pkdlog('error={} stack={}', e, pkdexc())

    def websocket_on_close(self):
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
        if self.websocket:
            if self.websocket == msg.handler:
                return
            self._websocket_free()
        self.websocket = msg.handler
        self.websocket.sr_driver_set(self)
        self.run_scheduler(self)

    def _subprocess_cmd_stdin_env(self, env=None, **kwargs):
        return job.subprocess_cmd_stdin_env(
            ('sirepo', 'job_agent'),
            PKDict(
                SIREPO_AUTH_LOGGED_IN_USER=self.uid,
                SIREPO_PKCLI_JOB_AGENT_AGENT_ID=self._agentId,
                SIREPO_PKCLI_JOB_AGENT_SUPERVISOR_URI=job.AGENT_ABS_URI,
#TODO(robnagler) dynamic
                SIREPO_SRDB_ROOT=sirepo.srdb.root(),
                **(env or {}),
            ),
            **kwargs,
        )

    def _websocket_free(self):
        """Remove holds on all resources and remove self from data structures"""
        try:
            del self.agents[self._agentId]
            self.instances[self.kind].remove(self)
            if self.has_slot:
                self.slot_free()
            w = self.websocket
            self.websockt = None
            if w:
                # Will not call websocket_on_close()
                w.sr_close()
            t = list(
                self.ops_pending_done.values()
                )
            t.extend(self.ops_pending_send)
            self.ops_pending_done.clear()
            self.ops_pending_send = []
            for o in t:
                o.set_errored('websocket closed')
            self.run_scheduler(self)
        except Exception as e:
            pkdlog('error={} stack={}', e, pkdexc())


async def get_instance(req):
    if req.kind == job.PARALLEL and req.jobRunMode == job.SBATCH:
        return await _CLASSES[job.SBATCH].get_instance(req)
    return await _DEFAULT_CLASS.get_instance(req)


def init():
    global _CLASSES, _DEFAULT_CLASS
    assert not _CLASSES
    _CLASSES = PKDict()
    p = pkinspect.this_module().__name__
    for n in job.cfg.drivers:
        m = importlib.import_module(pkinspect.module_name_join((p, n)))
        _CLASSES[n] = m.init_class()
    _DEFAULT_CLASS = _CLASSES.get('docker') or _CLASSES.get(job.DEFAULT_DRIVER)


async def terminate():
    await DriverBase.terminate()
