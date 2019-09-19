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
        self.agent_id = agent_id
        self.resource_class = resource_class
        self.message_handler = None
        self.message_handler_set = tornado.locks.Event()
        self.requests_to_send_to_agent = tornado.queues.Queue()
        tornado.ioloop.IOLoop.current().spawn_callback(self._process_requests_to_send_to_agent)

    @classmethod
    async def _enqueue_request(cls, request):
        request.request_reply_was_sent = tornado.locks.Event()
        dc = cls._get_driver_class(request)

        user_found = False
        for u in dc.requests[request.content.resource_class]:
            if u.uid == request.content.uid:
                pkdc('user {} found for request content uid {}', u, request.content.uid)
                u.requests.append(request)
                user_found = True
                break
        if not user_found:
            pkdc(
                'no user found for request content uid {} creating one in class {}',
                request.content.uid,
                request.content.resource_class
            )
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

    def _get_request(self, req_id):
        u = self._get_user()
        for r in u.requests:
            if r.content.rid == req_id:
                return r

        raise AssertionError(
            'req_id {} not found in requests {}',
            req_id,
            u.requests
        )

    def _get_user(self):
        for u in type(self).requests[self.resource_class]: # pylint: disable=no-member
            if u.uid == self.uid:
                return u
        raise AssertionError(
            'uid {} not found in requests {}',
            self.uid,
            type(self).requests[self.resource_class] # pylint: disable=no-member
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
        request.state = job_scheduler.STATE_EXECUTION_PENDING
        await cls._enqueue_request(request)

    async def _process_message(self, message):
        pkdp('message {}', message)
        a = message.content.get('action')
        if a == job.ACTION_READY_FOR_WORK:
            return
        elif a == 'protocol_error':
            # TODO(e-carlin): Handle more. If message has an rid we should
            # likely resend the request
            pkdlog('Error: {}', message)
            return

        pkdp('********************** {}', message)
        r = self._get_request(message.content.rid)
        pkdp('*************** {}', r)
        r.request_handler.write(message.content)
        r.request_reply_was_sent.set()
        self._remove_request(message.content.rid) 
        await job_scheduler.run(type(self), self.resource_class)

    async def _process_requests_to_send_to_agent(self):
        while True:
            r = await self.requests_to_send_to_agent.get()
            pkdc('request={}', self.agent_id)
            await self.message_handler_set.wait()
            self.message_handler.write_message(pkjson.dump_bytes(r.content))

    def _remove_request(self, req_id):
        u = self._get_user()
        r = self._get_request(req_id)
        u.requests.remove(r)


        from sirepo.driver import local
        pkdp('&&&&&&&&&&& {}',local.LocalDriver.requests)
