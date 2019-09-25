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


class DriverBase(object):
    driver_for_agent = pkcollections.Dict()

    def __init__(self, uid, agent_id, resource_class):
        # TODO(e-carlin): Do all of these fields need to be public? Doubtful...
        self.uid = uid
        self.agent_started = False
        self.agent_id = agent_id
        self.resource_class = resource_class
        self.message_handler = None
        self.message_handler_set = tornado.locks.Event()
        self.requests = []
        self.requests_to_send_to_agent = tornado.queues.Queue()
        # TODO(e-carlin): This is used to keep track of what run_dir currently
        # has a data job running in it. This makes it so we only send one data
        # job at a time. I think we should create a generalized data structure
        # that can store other types of cache information (ex what was the last
        # status). In addition they key is currently the run_dir. It needs to be
        # the "compute job name"
        self.running_data_jobs = set()
        tornado.ioloop.IOLoop.current().spawn_callback(self._process_requests_to_send_to_agent)

    async def _process_requests_to_send_to_agent(self):
        while True:
            r = await self.requests_to_send_to_agent.get()
            await self.message_handler_set.wait()
            self.message_handler.write_message(pkjson.dump_bytes(r.content))
