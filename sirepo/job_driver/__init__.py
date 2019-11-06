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

    def __init__(self, req, space):
        super().__init__(
            has_slot=False,
            has_ws=False,
            ops_pending_done=PKDict(),
            ops_pending_send=[],
            uid=req.content.uid,
            _agentId=job.unique_key(),
            _kind=space.kind,
            _space=space,
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
    async def get_instance(cls, req):
#TODO(robnagler) need to introduce concept of parked drivers for reallocation.
# a driver is freed as soon as it completes all its outstanding ops. For
# _run(), this is an outstanding op, which holds the driver until the _run()
# is complete. Same for analysis. Once all runs and analyses are compelte,
# free the driver, but park it. Allocation then is trying to find a parked
# driver then a free slot. If there are no free slots, we garbage collect
# parked drivers. We can park more drivers than are available for compute
# so has to connect to the max slots. Parking is only needed for resources
# we have to manage (local, docker). For NERSC, AWS, etc. parking is not
# necessary. You would allocate as many parallel slots. We can park more
# slots than are in_use, just can't use more slots than are actually allowed.

#TODO(robnagler) drivers are not organized by uid, because there can be more
# than one per user, rather, we can have a list here, not just self.
# need to have an allocation per user, e.g. 2 sequential and one 1 parallel.
# _Slot() may have to understand this, because related to parking. However,
# we are parking a driver so maybe that's a (local) driver mechanism
        for d in cls.instances[req.kind]:
            if d.uid == req.content.uid:
                return d
        return cls(req, await Space.allocate(req.kind))

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
    def init_class(cls, cfg):
        for k in job.KINDS:
            cls.slots[k] = PKDict(
                in_use=0,
                total=cfg[k + '_slots'],
            )
            cls.instances[k] = []
            Space.init_kind(k)
        return cls

    @classmethod
    def free_slots(cls, kind):
        for d in cls.instances[kind]:
            if d.has_slot and not d.ops_pending_send:
                cls.slots[kind].in_use -= 1
    @classmethod
    def receive(cls, msg):
        cls.agents[msg.content.agentId]._receive(msg)

# TODO(e-carlin): Take in a arg of driver and start the loop from the index
# of that driver. Doing so enables fair scheduling. Otherwise user at start of
# list always has priority
    @classmethod
    def run_scheduler(cls, kind):
        cls.free_slots(kind)
        for d in cls.instances[kind]:
            ops_with_send_alloc = d.get_ops_with_send_allocation()
            if not ops_with_send_alloc:
                continue
            if ((not d.has_slot and cls.slots[kind].in_use >= cls.slots[kind].total)
                or not d.has_ws
            ):
                continue
            if not d.has_slot:
                # if the driver doesn't have a slot then assign the slot to it
                d.has_slot = True
                cls.slots[kind].in_use += 1
            for o in ops_with_send_alloc:
                assert o.opId not in d.ops_pending_done
                d.ops_pending_send.remove(o)
                d.ops_pending_done[o.opId] = o
                o.send_ready.set()

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
    # TODO(e-carlin): parse req to get class
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
    assert not {'local', 'docker'}.issubset(cfg.modules), \
        'modules={} can only contain one of "docker" or "local"'.format(cfg.modules)
    assert 'local' or 'docker' in cfg.modules, \
        'modules={} must contain only one of "docker" or "local"'.format(cfg.modules)
    p = pkinspect.this_module().__name__
    _CLASSES = PKDict()
    for n in cfg.modules:
        m = importlib.import_module(pkinspect.module_name_join((p, n)))
        _CLASSES[n] = m.init_class()
    if 'docker' in cfg.modules:
        _DEFAULT_CLASS = _CLASSES['docker']
    else:
        _DEFAULT_CLASS = _CLASSES['local']


class Space(PKDict):
    """If a driver has a space then they have an alive agent but may not be
    actively performing an op.
    """

    in_use = PKDict()

    @classmethod
    async def allocate(cls, kind):
        self = cls(kind=kind)
        self.in_use[self.kind].append(self)
        return self

    @classmethod
    def init_kind(cls, kind):
        cls.in_use[kind] = []


def terminate():
    DriverBase.terminate()


