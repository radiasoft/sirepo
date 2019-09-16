# -*- coding: utf-8 -*-
"""TODO(e-carlin): Doc

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function

from pykern.pkdebug import pkdp, pkdc
from sirepo import driver
import uuid

STATE_EXECUTION_PENDING = 'state_execution_pending'
STATE_EXECUTING = 'state_executing'

async def run(driver_class, resource_class):
    pkdc('scheduler running for driver class {} and resource class {}', driver_class, resource_class)
    
    # TODO(e-carlin): think more about this algorithm. Quite simple right now.
    # TODO(e-carlin): Refactor so less nested
    # TODO(e-carlin): run status jobs are queued up in this q as well. I'm  still
    # not understanding how they will be actioned in a timely manner if this is
    # the case. Also, if a user starts multiple concurrent simulations we could
    # have deadlock where we can't get the status of the first simulation because
    # we are waiting on the execution of the second simulation but we won't 
    # know if the first simulation is done until we can know its status
    if _slots_available(driver_class, resource_class):
        pkdp('slots avail')
        for request_index in range(_len_longest_requests_q(driver_class.requests[resource_class])):
            pkdp('r indx {}', request_index)
            for u in driver_class.requests[resource_class]:
                pkdp('u {}', u)
                if not _any_requests_executing(u.requests):
                    pkdp('none executing')
                    if request_index < len(u.requests):
                        pkdp('still requests to iterate on')
                        r = u.requests[request_index]
                        if r.state != STATE_EXECUTION_PENDING:
                            pkdp('state exec pending')
                            continue
                        d = driver.DriverBase.resource_class_and_user_to_driver[resource_class].get(r.content.uid)
                        if not d:
                            pkdp('creating driver instance')
                            d = _create_driver_instance(r, resource_class, driver_class)
                        r.state = STATE_EXECUTING
                        await d.requests_to_send_to_agent.put(r)
                        if not _slots_available(driver_class, resource_class):
                            return

def _create_driver_instance(request, resource_class, driver_class):
    assert _slots_available(driver_class, resource_class)
    agent_id = str(uuid.uuid4())
    pkdc('no agent found for uid {} in resource class {}. Creating one', request.content.uid, resource_class)
    d = driver_class(request.content.uid, agent_id, resource_class)
    # TODO(e-carlin): It is annoying to keep agents mapped to agent id and to uid
    # Find a better structure for this 
    # TODO(e-carlin): We created a new driver which create a new agent. Decrement slots.
    driver.DriverBase.driver_for_agent[agent_id] = d
    driver.DriverBase.resource_class_and_user_to_driver[resource_class][request.content.uid] = d
    return d

def _slots_available(driver_class, resource_class):
    return driver_class.resource_manager[resource_class].slots > 0


def _len_longest_requests_q(user_queues):
    m = 0
    for u in user_queues:
        m = max(m, len(u.requests))
    return m

def _any_requests_executing(requests):
    for r in requests:
        if r.state == STATE_EXECUTING:
            return True
    return False