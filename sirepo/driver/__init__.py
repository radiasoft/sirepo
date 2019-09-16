# -*- coding: utf-8 -*-
"""TODO(e-carlin): Doc

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function

from pykern import pkcollections
from pykern import pkjson
from pykern.pkdebug import pkdp, pkdlog
from sirepo import job
from sirepo import job_scheduler
import tornado.ioloop
import tornado.locks
import tornado.locks
import tornado.queues
import uuid


class DriverBase(object):
    # TODO(e-carlin): This is botched. We also keep track of uid->agent in resource_manager
    agent_to_driver = pkcollections.Dict()

    def __init__(self, uid, agent_id, resource_class):
        self.uid = uid
        self.agent_id = agent_id
        self.resource_class = resource_class
        self.message_handler = None
        self.message_handler_set = tornado.locks.Event()
        self.requests_to_send_to_agent = tornado.queues.Queue()
        tornado.ioloop.IOLoop.current().spawn_callback(self._process_requests_to_send_to_agent)

    async def _process_requests_to_send_to_agent(self):
        while True:
            r = await self.requests_to_send_to_agent.get()
            await self.message_handler_set.wait()
            self.message_handler.write_message(pkjson.dump_bytes(r.content))

    @classmethod
    async def process_message(cls, message):
        d = cls.agent_to_driver[message.content.agent_id]
        if not d.message_handler_set.is_set():
            d.message_handler = message.message_handler
            d.message_handler_set.set()
        if message.content.action != job.ACTION_DRIVER_READY_FOR_WORK:
            await d.process_message(message)



    @classmethod
    async def process_request(cls, request):
        """
        request = {
            request_handler: tornado.RequestHandler.self,
            request_reply_was_sent: tornado.locks.Event()
            content: {
                uid: user id,
                rid: request id
                ...
            }
        }
        """
        request.state = job_scheduler.STATE_EXECUTION_PENDING
        await cls._enqueue_request(request)

    @classmethod
    async def _enqueue_request(cls, request):
        request.request_reply_was_sent = tornado.locks.Event()
        dc = cls._get_driver_class(request)

        user_found = False        
        for u in dc.requests[request.content.resource_class]:
            if u.uid == request.content.uid:
                u.requests.append(request)
                user_found = True
                break
        if not user_found:
            dc.requests[request.content.resource_class].append(pkcollections.Dict(
                uid=request.content.uid,
                requests = [request],
            ))
        await job_scheduler.run(dc, request.content.resource_class)
        await request.request_reply_was_sent.wait()
    
    @classmethod
    def _get_driver_class(cls, request):
        from sirepo.driver import local
        # TODO(e-carlin): Actually parse the request and get the class
        return local.LocalDriver


    # @classmethod
    # def _get_driver(cls, request):
    #     """Parse a request or message and gets the driver instance for it. Creates driver instance if none is found.

    #     A request is mapped to a driver based on:
    #         - request.uid
    #         - request.num_cores
    #         - request.driver_type # If no driver_type is specified then we will use local
    #                               # in development and docker in production
    #     """
    #     from sirepo.driver import local # TODO(e-carlin): circular dependency
    #     # TODO(e-carlin): Should we maintain a separate structure (or use a diff
    #     # data structure) so we don't have to do this kind of iteration? If we 
    #     # ever had a lot of users this could be a bottleneck
    #     # we could use a dict with key user id and value list and the list is the
    #     # same one as in the self.requests

    #     driver_type = local.LocalDriver # TODO(e-carlin): Figure out class of driver from request
    #     for d in driver_type.instances:
    #         if d.uid == request.content.uid:
    #             return d

    #     d = driver_type(request.content.uid)
    #     driver_type.instances.append(d)
    #     return d



            
    