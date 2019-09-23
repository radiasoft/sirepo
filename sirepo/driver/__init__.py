# -*- coding: utf-8 -*-
"""TODO(e-carlin): Doc

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkcollections
from pykern import pkjson
from pykern.pkdebug import pkdp, pkdlog, pkdc
from sirepo import job
from sirepo import job_scheduler
import tornado.ioloop
import tornado.locks
import tornado.locks
import tornado.queues
import uuid


class DriverBase(object):
    driver_for_agent = pkcollections.Dict()

    # TODO(e-carlin): This will likely change once I have a better understanding of
    # how we will map server job requests to a driver
    resource_class_and_user_to_driver = pkcollections.Dict(
        sequential=pkcollections.Dict(),
        parallel=pkcollections.Dict(),
    )

    def __init__(self, uid, agent_id, resource_class):
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

    @classmethod
    async def _enqueue_request(cls, request):
        request.request_reply_was_sent = tornado.locks.Event()
        dc = cls._get_driver_class(request)

        for d in dc.resources[request.content.resource_class].drivers:
            if d.uid == request.content.uid:
                d.requests.append(request)
                break
        else:
            d = dc(
                request.content.uid,
                str(uuid.uuid4()),
                request.content.resource_class
            )
            d.requests.append(request)
            dc.resources[request.content.resource_class].drivers.append(d)
            cls.driver_for_agent[d.agent_id] = d

        await job_scheduler.run(dc, request.content.resource_class)
        await request.request_reply_was_sent.wait()


    @classmethod
    def _get_driver_class(cls, request):
        from sirepo.driver import local
        # TODO(e-carlin): Actually parse the request and get the class
        return local.LocalDriver

    def _get_request(self, req_id):
        d = self._get_driver()
        for r in d.requests:
            if r.content.req_id == req_id:
                return r

        raise AssertionError(
            'req_id {} not found in requests {}',
            req_id,
            d.requests
        )

    def _get_driver(self):
        for d in type(self).resources[self.resource_class].drivers: # pylint: disable=no-member
            if d.uid == self.uid:
                return d
        raise AssertionError(
            'uid {} not found in drivers {}',
            self.uid,
            type(self).resources[self.resource_class].drivers, # pylint: disable=no-member
        )

    @classmethod
    async def incoming_message(cls, message):
        d = cls.driver_for_agent[message.content.agent_id]
        if not d.message_handler_set.is_set():
            d.message_handler = message.message_handler
            d.message_handler_set.set()
        await d._process_message(message)

    @classmethod
    async def incoming_request(cls, request):
        request.state = 'execution_pending'
        await cls._enqueue_request(request)

    async def _process_message(self, message):
        a = message.content.get('action')
        if a == job.ACTION_READY_FOR_WORK:
            return
        elif a == 'protocol_error':
            # TODO(e-carlin): Handle more. If message has a req_id we should
            # likely resend the request
            pkdlog('Error: {}', message)
            return

        r = self._get_request(message.content.req_id)
        r.request_handler.write(message.content)
        r.request_reply_was_sent.set()
        self._remove_request(message.content.req_id) 

        # TODO(e-carlin): This is quite hacky. The logic to add is in scheduler
        # but logic to remove is here which is not great. These ifs aren't robust
        # what will happen when types of jobs are updated?
        # clear out running data jobs
        if r.content.action == job.ACTION_COMPUTE_JOB_STATUS:
            if message.content.status != job.JobStatus.RUNNING.value:
                self.running_data_jobs.discard(r.content.compute_model_name)
        elif r.content.action == job.ACTION_RUN_EXTRACT_JOB:
            self.running_data_jobs.discard(r.content.compute_model_name)


        await job_scheduler.run(type(self), self.resource_class)

    async def _process_requests_to_send_to_agent(self):
        while True:
            r = await self.requests_to_send_to_agent.get()
            await self.message_handler_set.wait()
            self.message_handler.write_message(pkjson.dump_bytes(r.content))

    def _remove_request(self, req_id):
        d = self._get_driver()
        r = self._get_request(req_id)
        d.requests.remove(r)
