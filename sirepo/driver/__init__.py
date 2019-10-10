# -*- coding: utf-8 -*-
"""TODO(e-carlin): Doc

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkconfig, pkio, pkinspect, pkcollections, pkconfig, pkjson
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdlog, pkdc
import sirepo.job
from sirepo import job_supervisor, simulation_db
import aenum
import importlib
import tornado.ioloop
import tornado.locks
import tornado.queues


#: map of driver names to class
_CLASSES = None


#: default class when not determined by request
_DEFAULT_CLASS = None


cfg = None


def get_class(job):
    return _DEFAULT_CLASS


async def get_instance_for_job(job):
    """Get a driver instance for a job.

    The method blocks until a driver can be freed.
    """
    return await get_class(job.req).get_instance_for_job(job)


def get_instance_for_agent(agent_id):
    return DriverBase.instances.get(agent_id)


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
            'how agents connect to supervisor',
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


def terminate():
    pkdp('TODO: implement terminate')
    # if pkconfig.channel_in('dev'):
    #     for k in DriverBase.instances.keys():
    #         if 'local' in k:
    #             for d in DriverBase.instances[k].values()


class Status(aenum.Enum):
    IDLE = 'idle'
    KILLING = 'killing'
    COMMUNICATING = 'communicating'
    STARTING = 'starting'


STATUS_IS_RUN = (Status.STARTING, Status.COMMUNICATING, Status.IDLE)


# TODO(e-carlin): Make this an abstract base class?
class DriverBase(PKDict):
    # TODO(e-carlin): Instances is overloaded. Has keys of agent_id and kind:uid
    instances = pkcollections.Dict()

    def __init__(self, *args, **kwargs):
        super().__init__(
            agent_id=sirepo.job.unique_key(),
            ops=PKDict(),
            send_lock=tornado.locks.BoundedSemaphore(1),
            sender=None,
            _handler=None,
            _handler_set=tornado.locks.Event(),
            _status=Status.IDLE,
            **kwargs,
        )
        self.instances[self.agent_id] = self

    def set_handler(self, handler):
        if not self._handler_set.is_set():
            self._handler_set.set()
            self._handler = handler

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
