# -*- coding: utf-8 -*-
"""TODO(e-carlin): Doc

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkjson, pkconfig, pkcollections
from pykern.pkdebug import pkdp, pkdlog, pkdc
from sirepo import job
from sirepo import job_supervisor
import importlib
import tornado.ioloop
import tornado.locks
import tornado.locks
import tornado.queues
import uuid


# TODO(e-carlin): Make this an abstract base class?
class DriverBase(object):
    driver_for_agent = pkcollections.Dict()

    def __init__(self, uid, resource_class):
        # TODO(e-carlin): Do all of these fields need to be public? Doubtful...
        self.uid = uid
        self.agent_id = str(uuid.uuid4())
        self.resource_class = resource_class
        self._message_handler_set = tornado.locks.Event()
        self.requests = []
        self.requests_to_send_to_agent = tornado.queues.Queue()
        # TODO(e-carlin): This is used to keep track of what run_dir currently
        # has a data job running in it. This makes it so we only send one data
        # job at a time. I think we should create a generalized data structure
        # that can store other types of cache information (ex what was the last
        # status). In addition they key is currently the run_dir. It needs to be
        # the "compute job name"
        self.running_data_jobs = set()
        self._agent_starting = False
        self._agent_started_waiters = pkcollections.Dict()
        self._message_handler = None
        tornado.ioloop.IOLoop.current().spawn_callback(self._process_requests_to_send_to_agent)

    def agent_started(self):
        return self._agent.agent_started

    def kill_agent(self):
        pkdlog('agent_id={}', self.agent_id)
        self._agent.kill()
        self._message_handler = None
        self._message_handler_set.clear()

    def on_ws_close(self):
        pkdlog('agent_id={}', self.agent_id)
        self._set_agent_stopped_state()
        for r in self.requests:
            # TODO(e-carlin): Think more about this. If the kill was requested
            # maybe the jobs are running too long? If the kill wasn't requested
            # maybe the job can't be run and is what is causing the agent to
            # die?
            if r.state == job_supervisor._STATE_RUNNING:
                r.state = job_supervisor._STATE_RUN_PENDING
        job_supervisor.run_scheduler(type(self), self.resource_class)

    def set_message_handler(self, message_handler):
        if not self._message_handler_set.is_set():
            self._agent_starting = False
            self._agent.agent_started = True
            self._message_handler = message_handler
            self._message_handler_set.set()
            message_handler._driver = self

    def start_agent(self, request):
        pkdlog('agent_id={}', self.agent_id)
        if self._agent_starting:
            return
        self._agent_starting = True
        self._agent.start(self._on_agent_error_exit)
        # claim the slot before the agent has actually started so we don't
        # accidentally give away 1 slot to 2 agents
        self.resources[self.resource_class].slots.in_use[self.agent_id] = self

    def _on_agent_error_exit(self, returncode):
        pkdlog('agent={} exited with returncode={}', self.agent_id, returncode)
        self._set_agent_stopped_state()
        for r in self.requests:
            r.set_response(
                pkcollections.Dict(
                    error='agent exited with returncode {}'.format(returncode)
                )
            )
        job_supervisor.run_scheduler(type(self), self.resource_class) # TODO(e-carlin): Is this necessary?

    async def _process_requests_to_send_to_agent(self):
        # TODO(e-carlin): Exception handling
        while True:
            r = await self.requests_to_send_to_agent.get()
            await self._message_handler_set.wait()
            self._message_handler.write_message(pkjson.dump_bytes(r.content))

    def _set_agent_stopped_state(self):
        # TODO(e-carlin): This method is a code smell. I just clear out everything
        # so I know we're in a good state. Maybe I should know the actual state
        # of the agent/driver a bit better and only change things that need to
        # be changed?
        self._agent_starting = False
        self._agent.agent_started = False
        self._message_handler = None
        self._message_handler_set.clear()
        # TODO(e-carlin): It is a hack to use pop. We should know more about
        # when an agent is running or not. It is done like this currently 
        # because it is unclear when on_agent_error_exit vs on_ws_close it called
        self.resources[self.resource_class].slots.in_use.pop(self.agent_id, None)

    @classmethod
    def enqueue_request(cls, req):
        dc = cls.get_driver_class(req)
        for d in dc.resources[req.content.resource_class].drivers:
            if d.uid == req.content.uid:
                d.requests.append(req)
                break
        else:
            d = dc(
                req.content.uid,
                req.content.resource_class
            )
            d.requests.append(req)
            dc.resources[req.content.resource_class].drivers.append(d)
            cls.driver_for_agent[d.agent_id] = d

    @classmethod
    def get_driver_class(cls, req):
        # TODO(e-carlin): Handle nersc and sbatch. Request will need to be parsed
        t = 'docker' if pkconfig.channel_in('alpha', 'beta', 'prod') else 'local'
        m = importlib.import_module(
            f'sirepo.driver.{t}'
        )
        return getattr(m, f'{t.capitalize()}Driver')
    
    @classmethod
    def dequeue_request(cls, req):
        dc = cls.get_driver_class(req)
        for d in dc.resources[req.content.resource_class].drivers:
            if d.uid == req.content.uid:
                d.requests.remove(req)
                break
        else:
            raise AssertionError(
                'req={}. Could not be removed because it was not found.',
                req
            )

