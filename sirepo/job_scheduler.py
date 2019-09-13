# -*- coding: utf-8 -*-
"""TODO(e-carlin): Doc

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function

from pykern.pkdebug import pkdp

STATE_EXECUTION_PENDING = 'state_execution_pending'
STATE_EXECUTING = 'state_executing'

def run(driver_class, parallel):
    resource_class = 'parallel' if parallel else 'sequential'
    available_slots = driver_class.resouce_manager.resouce_class.slots
    if available_slots == 0:
        # We hjave no resources so no work can be submitted
        return

    # TODO(e-carlin): This algorithm does all of a users jobs before going to the
    # next user. Not very fair    
    for u in driver_class.requests.resouce_class:
        for r in u.requests:
            if r.state == STATE_EXECUTION_PENDING:
                continue
            # here we want to submit the job to the driver
            d = driver_class.resouce_manager.resouce_class.agents.get(r.content.uid)
            if not d:
                d = driver_class(r.content.uid)
            r.state = STATE_EXECUTING
            d.requests_to_send_to_agent.put_nowait(r)

    pkdp(driver_class.resouce_manager.resouce_class.agents)
    pkdp(driver_class.resouce_manager.resouce_class.requests)

    # for d in driver_instances:
    #     for r in d.requests:
    #         # TODO(e-carlin): Should we use put_nowait? I think so so the
    #         # scheduler should run syncronously because it needs to know all of
    #         # the state and if the state changes out from under it that could
    #         # be problematic
    #         d.requests_to_send_to_agent.put_nowait(r)