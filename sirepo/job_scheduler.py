# -*- coding: utf-8 -*-
"""TODO(e-carlin): Doc

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function

from pykern.pkdebug import pkdp
from sirepo import driver
import uuid

STATE_EXECUTION_PENDING = 'state_execution_pending'
STATE_EXECUTING = 'state_executing'

async def run(driver_class, resource_class):
    pkdp('running')
    available_slots = driver_class.resource_manager[resource_class].slots
    if available_slots == 0:
        # We have no resources so no work can be submitted
        pkdp('no slots available {}', driver_class.resource_manager[resource_class])
        return

    # TODO(e-carlin): This algorithm does all of a users jobs before going to the
    # next user. Not very fair    
    for u in driver_class.requests[resource_class]:
        for r in u.requests:
            if r.state != STATE_EXECUTION_PENDING:
                continue
            # here we want to submit the job to the driver
            d = driver_class.resource_manager[resource_class].agents.get(r.content.uid)
            if not d:
                agent_id = str(uuid.uuid4())
                d = driver_class(r.content.uid, agent_id, resource_class)
                # TODO(e-carlin): It is annoying to keep agents mapped to agent id and to uid
                # Find a better structure for this 
                driver.DriverBase.agent_to_driver[agent_id] = d
                driver_class.resource_manager[resource_class].agents[r.content.uid] = d
            r.state = STATE_EXECUTING
            # TODO(e-carlin): decrement slots
            await d.requests_to_send_to_agent.put(r)
