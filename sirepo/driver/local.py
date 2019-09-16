# -*- coding: utf-8 -*-
"""TODO(e-carlin): Doc

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function

from sirepo import driver
from pykern.pkdebug import pkdp, pkdlog
from pykern import pkcollections
import tornado.process
from sirepo import job
from pykern import pkconfig
import sirepo.mpi
from sirepo import job_scheduler


class LocalDriver(driver.DriverBase):
        # """
        # # agents = {
        # #     uid : instance of LocalDriver
        # # }
        # """
    """
    requests.parallel = [
        {
            uid: abc123,
            requests = [

                {
                    request_handler: tornado.RequestHandler.self,
                    request_reply_was_sent: tornado.locks.Event()
                    content: {
                        uid: user id,
                        rid: request id
                        ...
                }
            ] 
        }
    ]
    """
    requests = pkcollections.Dict(
        parallel=[],
        sequential=[],
    )
    resource_manager = pkcollections.Dict(
        # TODO(e-carlin): Take slots from cfg
        parallel=pkcollections.Dict(slots=1, in_use=0, agents={}),
        sequential=pkcollections.Dict(slots=1, in_use=0, agents={}),
    )
    instances = pkcollections.Dict()
    def __init__(self, uid, agent_id, resource_class):
        super(LocalDriver, self).__init__(uid, agent_id, resource_class)
        
        # TODO(e-carlin): Make this more robust. Ex handle failures, monitor the created process.
        tornado.process.Subprocess(
            [
                'sirepo',
                'job_agent',
                'start',
                self.agent_id,
                cfg.supervisor_ws_uri,
            ]
        )

    async def process_message(self, message):
        # TODO(e-carlin): This should probably live in DriverBase

        # TODO(e-carlin): Should an instance of a driver know more about its requests?
        # it feels funny to iterate over all requests in an instance of the class
        for u in self.requests[self.resource_class]:
            if u.uid != self.uid:
                continue
            for r in u.requests:
                if r.content.rid == message.content.rid:
                    r.request_handler.write(message.content)
                    r.request_reply_was_sent.set()
                    u.requests.remove(r)
                    # await job_scheduler.run(self.instances)
                    return
                    
        raise AssertionError(
            'the message {} did not have a corresponding request in requests {}'.format(
            message,
            self.requests[self.resource_class],
            ))


cfg = pkconfig.init(
    supervisor_ws_uri=(
        job.cfg.supervisor_ws_uri, 
        str, 
        'uri to reach the supervisor for websocket connections',
    ),
)
