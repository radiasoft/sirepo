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
    pkdc('slots available? {}', _slots_available(driver_class, resource_class))

    # TODO(e-carlin): this needs a lot of work    
    # TODO(e-carlin): run status jobs are queued up in this q as well. I'm  still
    # not understanding how they will be actioned in a timely manner if this is
    # the case. Also, if a user starts multiple concurrent simulations we could
    # have deadlock where we can't get the status of the first simulation because
    # we are waiting on the execution of the second simulation but we won't 
    # know if the first simulation is done until we can know its status
    for request_index in range(_len_longest_requests_q(driver_class.requests[resource_class])):
        for u in driver_class.requests[resource_class]:
            if not _any_requests_executing(u.requests):
                if request_index < len(u.requests):
                    r = u.requests[request_index]
                    if r.state != STATE_EXECUTION_PENDING:
                        continue
                    d = driver.DriverBase.resource_class_and_user_to_driver[resource_class].get(r.content.uid)
                    if d is None:
                        if _slots_available(driver_class, resource_class):
                            d = _create_driver_instance(r, resource_class, driver_class)
                        else:
                            continue
                    r.state = STATE_EXECUTING
                    await d.requests_to_send_to_agent.put(r)

def _create_driver_instance(request, resource_class, driver_class):
    assert _slots_available(driver_class, resource_class)
    agent_id = str(uuid.uuid4())
    pkdc('no agent found for uid {} in resource class {}. Creating one', request.content.uid, resource_class)
    d = driver_class(request.content.uid, agent_id, resource_class)
    # TODO(e-carlin): It is annoying to keep agents mapped to agent id and to uid
    # Find a better structure for this 
    # TODO(e-carlin): We created a new driver which create a new agent. Decrement slots.
    driver_class.resource_manager[resource_class].slots_in_use += 1
    driver.DriverBase.driver_for_agent[agent_id] = d
    driver.DriverBase.resource_class_and_user_to_driver[resource_class][request.content.uid] = d
    return d

def _slots_available(driver_class, resource_class):
    resource = driver_class.resource_manager[resource_class]
    return resource.slots_in_use < resource.total_slots


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