# -*- coding: utf-8 -*-
"""TODO(e-carlin): Doc

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkcollections
from pykern import pkconfig
from pykern import pkinspect
from pykern import pkjson
from pykern import pkjson, pkconfig, pkcollections
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdlog, pkdc
from sirepo import job
from sirepo import job_supervisor
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

def get_class(req):
    return _DEFAULT_CLASS


def get_instance(msg):
    d = DriverBase.instances[msg.content.agent_id]
    if not d._handler_set.is_set():
        d._status = Status.COMMUNICATING
        d._handler = msg.handler
        d._handler_set.set()
        #rn so driver gets on_close callback
        msg.handler.driver = d
    return d


def get_kind(req):
    return get_class(req).KIND


def init():
    global _CLASSES, _DEFAULT_CLASS, cfg
    assert not _CLASSES
    cfg = pkconfig.init(
        modules=(('local',), set, 'driver modules'),
        supervisor_uri=(
            'ws://{}:{}{}'.format(job.DEFAULT_IP, job.DEFAULT_PORT, job.AGENT_URI),
            str,
            'how agents connect to supervisor',
        ),
    )
    this_module = pkinspect.this_module()
    p = pkinspect.this_module().__name__
    _CLASSES = PKDict()
    for n in cfg.modules:
        m = importlib.import_module(pkinspect.module_name_join((p, n)))
        _CLASSES[n] = m.init_class()
    # when we support more than one class, we 'll have to define
    # _DEFAULT_CLASS some how
    assert len(_CLASSES) == 1
    _DEFAULT_CLASS = list(_CLASSES.values())[0]
    return


def terminate():
    if pkconfig.channel_in('dev'):
        for d in DriverBase.instances.values():
            d.kill()


class Status(aenum.Enum):
    IDLE = 'idle'
    KILLING = 'killing'
    COMMUNICATING = 'communicating'
    STARTING = 'starting'


STATUS_IS_RUN = (Status.STARTING, Status.COMMUNICATING, Status.IDLE)


# TODO(e-carlin): Make this an abstract base class?
class DriverBase(PKDict):
    instances = pkcollections.Dict()

    def __init__(self, *args, **kwargs):
        # TODO(e-carlin): Do all of these fields need to be public? Doubtful...
        super().__init__(
            agent_id=job.unique_key(),
            _status=Status.IDLE,
            _handler_set=tornado.locks.Event(),
            _handler=None,
            requests=[],
            requests_to_send_to_agent=tornado.queues.Queue(),
            **kwargs,
        )
        # TODO(e-carlin): This is used to keep track of what run_dir currently
        # has a data job running in it. This makes it so we only send one data
        # job at a time. I think we should create a generalized data structure
        # that can store other types of cache information (ex what was the last
        # status). In addition they key is currently the run_dir. It needs to be
        # the "compute job name"
        self.running_data_jobs = set()
        tornado.ioloop.IOLoop.current().spawn_callback(
            self._process_requests_to_send_to_agent
        )

    def dequeue_request(self, req):
        assert self.uid == req.content.uid, \
            'req={} uid does not match driver={}'.format(req, self)
        self.requests.remove(req)

    @classmethod
    def enqueue_request(cls, req):
        for d in cls.resources[req.content.resource_class].drivers:
            if d.uid == req.content.uid:
                break
        else:
            d = cls(
                uid=req.content.uid,
                resource_class=req.content.resource_class,
                supervisor_uri=cfg.supervisor_uri,
            )
            d.resources[d.resource_class].drivers.append(d)
            cls.instances[d.agent_id] = d
        d.requests.append(req)
        return d

    def is_started(self):
        return self._status in (Status.COMMUNICATING, Status.KILLING)

    def kill(self):
        pkdlog('{}', self)
        self._kill()
        self._handler = None
        self._handler_set.clear()

    def on_close(self):
        pkdlog('agent_id={}', self.agent_id)
#rn will need to kill just in case socket closed not due to process exit
        self._set_agent_stopped_state()
        job_supervisor.restart_requests(self)
        job_supervisor.run_scheduler(self)

    def start(self, request):
        pkdlog('agent_id={}', self.agent_id)
#rn why not an assert?
        if self._status == Status.STARTING:
            return
        self._status = Status.STARTING
        # claim the slot before the agent has actually started so we don't
        # accidentally give away 1 slot to 2 agents
        self.resources[self.resource_class].slots.in_use[self.agent_id] = self
        self._start()

    def _on_agent_error_exit(self):
        pkdlog('agent={}', self.agent_id)
        self._set_agent_stopped_state()
        for r in self.requests:
            r.set_response(
                pkcollections.Dict(
                    error='agent exited with returncode {}'.format(returncode)
                )
            )
        job_supervisor.run_scheduler(self)

    async def _process_requests_to_send_to_agent(self):
        # TODO(e-carlin): Exception handling
        while True:
            r = await self.requests_to_send_to_agent.get()
            await self._handler_set.wait()
            self._handler.write_message(pkjson.dump_bytes(r.content))

    def _set_agent_stopped_state(self):
        # TODO(e-carlin): This method is a code smell. I just clear out everything
        # so I know we're in a good state. Maybe I should know the actual state
        # of the agent/driver a bit better and only change things that need to
        # be changed?
        self._status = Status.IDLE
        self._handler = None
        self._handler_set.clear()
        # TODO(e-carlin): It is a hack to use pop. We should know more about
        # when an agent is running or not. It is done like this currently
        # because it is unclear when on_agent_error_exit vs on_ws_close it called
        self.resources[self.resource_class].slots.in_use.pop(self.agent_id, None)

    def __repr__(self):
        return 'class={} resource_class={} uid={} status={} agent_id={} slots_available={}'.format(
            type(self),
            self.uid,
            self._status,
            self.resource_class,
            self.slots_available(),
            self.agent_id,
        )
