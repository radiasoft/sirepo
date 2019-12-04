# -*- coding: utf-8 -*-
"""Base for drivers

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
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

_DEFAULT_MODULE = 'local'

cfg = None


class AgentMsg(PKDict):

    async def receive(self):
        # Agent messages do not block the supervisor
        DriverBase.receive(self)


class DriverBase(PKDict):

    agents = PKDict()

    def __init__(self, req):
        super().__init__(
            _agentId=job.unique_key(),
            kind=req.kind,
            ops_pending_done=PKDict(),
            ops_pending_send=[],
            uid=req.content.uid,
            websocket=None,
        )
        self.agents[self._agentId] = self
        pkdlog(
            'class={} agentId={_agentId} kind={kind} uid={uid}',
            self.__class__.__name__,
            **self
        )

    def cancel_op(self, op):
        for o in self.ops_pending_send:
            if o == op:
                self.ops_pending_send.remove(o)
#rjn there should only be one op
                return
#rjn it's cheaper to create a list of values (list(x.values()) than a copy of the whole dict.
#   but we don't need to do that because we are going to exit once found
        for o in self.ops_pending_done.values():
            if o == op:
                del self.ops_pending_done[o.opId]
#rjn there should only be one op
                return
#rjn is this a valid assumption?
        raise AssertionError('could not find opId={} for agentId={}'.format(o.opId, self._agentId))

    def destroy_op(self, op):
        assert op not in self.ops_pending_send
        # canceled ops are removed in self.cancel_op()
        if not op.canceled and not op.errored:
            del self.ops_pending_done[op.opId]
        self.run_scheduler()

    def get_ops_pending_done_types(self):
        d = collections.defaultdict(int)
        for v in self.ops_pending_done.values():
            d[v.msg.opName] += 1
        return d

    def get_ops_with_send_allocation(self):
        """Get ops that could be sent assuming outside requirements are met.
        Outside requirements driver having a slot.
        """
        if not self.websocket:
            return []
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
    def receive(cls, msg):
        a = cls.agents.get(msg.content.agentId)
        if not a:
            pkdlog('unknown agent msg={}, sending kill', msg)
            try:
                msg.handler.write_message(PKDict(opName=job.OP_KILL))
            except Exception as e:
                pkdlog('error={} stack={}', e, pkdexc())
        a._receive(msg)

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
        self.run_scheduler()
        await op.send_ready.wait()
        if op.opId in self.ops_pending_done:
            pkdlog('op={} agentId={} opId={}', op.opName, self._agentId, op.opId)
            self.websocket.write_message(pkjson.dump_bytes(op.msg))
        else:
            pkdlog('canceled op={}', job.LogFormatter(op))
        assert op not in self.ops_pending_send

    @classmethod
    async def terminate(cls):
        for d in DriverBase.agents.copy().values():
            try:
#TODO(robnagler) need a timeout on each kill or better do not await
# here, but send all the kills (scheduling callbacks) and then set
# a timer callback to do the loop exit in pkcli.job_supervisor
# with callbacks from the driver saying they've terminated cleanly.
# this allows a clean callback case for sbatch, which would be nice
# to get an ack to the clean termination, because it needs to remove
# stuff from the queue, and it would be good to know about that
                await d.kill()
            except Exception as e:
                # If one kill fails still try to kill the rest
                pkdlog('error={} stack={}', e, pkdexc())

    def websocket_on_close(self):
       self.websocket_free()

    def _receive(self, msg):
        c = msg.content
        i = c.get('opId')
        if c.opName == job.OP_ERROR:
            pkdlog('agentId={} msg={}',self._agentId, c)
        else:
            pkdlog('{} agentId={} opId={}', c.opName, self._agentId, i)
        if i:
            if 'reply' not in c:
                pkdlog('agentId={} No reply={}', self._agentId, c)
                c.reply = PKDict(state='error', error='no reply')
            if i in self.ops_pending_done:
                self.ops_pending_done[i].reply_put(c.reply)
            else:
                pkdlog('agentId={} not pending opId={} opName={}', self._agentId, i, c.opName)
        else:
            getattr(self, '_receive_' + c.opName)(msg)

    def _receive_error(self, msg):
        pkdlog('agentId={} msg={}', self._agentId, msg)

    def _receive_alive(self, msg):
        """Receive an ALIVE message from our agent

        Save the websocket and register self with the websocket
        """
        if self.websocket:
            if self.websocket == msg.handler:
#TODO(robnagler) do we want to run_scheduler on alive in all cases?
#                self.run_scheduler()
                return
            self.websocket_free()
        self.websocket = msg.handler
        self.websocket.sr_driver_set(self)
#TODO(robnagler) do we want to run_scheduler on alive in all cases?
        self.run_scheduler()

    def _agent_cmd_stdin_env(self, env=None, **kwargs):
        return job.agent_cmd_stdin_env(
            ('sirepo', 'job_agent'),
            env=self._agent_env(),
            **kwargs,
        )

    def _agent_env(self, env=None):
        return job.agent_env(
            env=(env or PKDict()).pksetdefault(
                SIREPO_PKCLI_JOB_AGENT_AGENT_ID=self._agentId,
                SIREPO_PKCLI_JOB_AGENT_SUPERVISOR_URI=job.AGENT_ABS_URI,
            ),
            uid=self.uid,
        )

    def websocket_free(self):
        """Remove holds on all resources and remove self from data structures"""
        try:
            del self.agents[self._agentId]
            w = self.websocket
            self.websocket = None
            if w:
                # Will not call websocket_on_close()
                w.sr_close()
            t = list(self.ops_pending_done.values()) + self.ops_pending_send
            self.ops_pending_done.clear()
            self.ops_pending_send.clear()
            for o in t:
                o.set_errored('websocket closed')
#TODO(robnagler) when the websocket disappears unexpectedly, we don't
# know that any resources are freed. With docker and local, we can check.
# For sbatch, we need to ask the user to login again.
            self._websocket_free()
        except Exception as e:
            pkdlog('error={} stack={}', e, pkdexc())


async def get_instance(req, jobRunMode):
    if jobRunMode == job.SBATCH:
        return await _CLASSES[job.SBATCH].get_instance(req)
    return await _DEFAULT_CLASS.get_instance(req)


def init():
    global cfg, _CLASSES, _DEFAULT_CLASS
    assert not cfg
    cfg = pkconfig.init(
        modules=((_DEFAULT_MODULE,), set, 'available job driver modules'),
    )
    _CLASSES = PKDict()
    p = pkinspect.this_module().__name__
    for n in cfg.modules:
        m = importlib.import_module(pkinspect.module_name_join((p, n)))
        _CLASSES[n] = m.init_class()
    _DEFAULT_CLASS = _CLASSES.get('docker') or _CLASSES.get(_DEFAULT_MODULE)


async def terminate():
    await DriverBase.terminate()
