# -*- coding: utf-8 -*-
"""TODO(e-carlin): Doc

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkconfig, pkio, pkinspect, pkcollections, pkconfig, pkjson
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdlog, pkdc
from sirepo import job_supervisor, simulation_db
import aenum
import importlib
import sirepo.job
import time
import tornado.ioloop
import tornado.locks
import tornado.queues


#: map of driver names to class
_CLASSES = None


#: default class when not determined by request
_DEFAULT_CLASS = None


cfg = None


class DriverBase(PKDict):
    instances = pkcollections.Dict()
    driver_for_agents = PKDict()

    def __init__(self, slot, job, *args, **kwargs):
        a = sirepo.job.unique_key()
        super().__init__(
            agent_id=a,
            jobs=[job],
            killing=False,
            kind=job.req.driver_kind,
            ops=PKDict(),
            send_lock=tornado.locks.BoundedSemaphore(1),
            sender=None,
            slot=slot,
            _agent_dir=job.req.agent_dir.format(agent_id=a),
            _agent_exited=tornado.locks.Event(),
            _handler=None,
            _handler_set=tornado.locks.Event(),
            _max_start_attempts=2,
            _start_attempts=0,
            _status=Status.IDLE,
            _terminate_timeout=None,
            **kwargs,
        )
        self.driver_for_agents[self.agent_id] = self
        self.instances[slot.kind][job.req.uid] = self

    async def do_op(self, **kwargs):
        kwargs.setdefault('op_id', sirepo.job.unique_key())
        m = PKDict(kwargs)
        o = job_supervisor.Op(msg=m)
        self.ops[m.op_id] = o
        await self.send_lock.acquire()
        # TODO(e-carlin): Clunky to have send_lock and handler_set
        await self._handler_set.wait()
        await self._handler.write_message(pkjson.dump_bytes(m))
        r = await o.get_result()
        self.send_lock.release()
        return r

    @classmethod
    def get_kind(cls, resource_class):
        assert resource_class in ('sequential', 'parallel')
        return resource_class + '-' + cls.module_name

    def __repr__(self):
        return 'class={} resource_class={} uid={} status={} agent_id={} slots_available={}'.format(
            type(self),
            self.uid,
            self._status,
            self.resource_class,
            self.slots_available(),
            self.agent_id,
        )

    def set_handler(self, handler):
        if not self._handler_set.is_set():
            self._handler_set.set()
            self._handler = handler

    def set_state(self, msg):
        # TODO(e-carlin): handle other types of messages with state
        m = msg.copy()
        del m['agent_id']
        del m['op']
        m.pop('op_id', None)
        jid = msg.get('jid')
        if jid:
            for j in self.jobs:
                if jid == j.jid:
                    j.res.update(**msg)
                    return


def get_class(job):
    return _DEFAULT_CLASS


def get_instance_for_agent(agent_id):
    return DriverBase.driver_for_agents.get(agent_id)


async def get_instance_for_job(job):
    """Get a driver instance for a job.

    The method blocks until a driver can be freed.
    """
    return await get_class(job).get_instance_for_job(job)


def get_kind(req):
    return get_class(req).get_kind(req.content.resource_class)


def init():
    global _CLASSES, _DEFAULT_CLASS, cfg
    assert not _CLASSES
    import types
    cfg = pkconfig.init(
        modules=(('local',), set, 'driver modules'),
        supervisor_uri=(
            'ws://{}:{}{}'.format(sirepo.job.DEFAULT_IP,
                                  sirepo.job.DEFAULT_PORT, sirepo.job.AGENT_URI),
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


class Status(aenum.Enum):
    COMMUNICATING = 'communicating'
    IDLE = 'idle'
    KILLING = 'killing'
    STARTING = 'starting'


def terminate():
    if pkconfig.channel_in('dev'):
        for k in DriverBase.instances.keys():
            if 'local' in k:
                for d in DriverBase.instances[k].values():
                    d.kill()