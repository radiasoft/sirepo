# -*- coding: utf-8 -*-
"""TODO(e-carlin): Doc

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function

from pykern.pkdebug import pkdp, pkdc
from sirepo import driver, job
import uuid

STATE_EXECUTION_PENDING = 'execution_pending'
STATE_EXECUTING = 'executing'

DATA_ACTIONS = [
    job.ACTION_RUN_EXTRACT_JOB,
    job.ACTION_START_COMPUTE_JOB,
]

_OPERATOR_ACTIONS = [
    job.ACTION_CANCEL_JOB,
]


async def run(driver_class, resource_class):
    pkdc('scheduler running for driver class {} and resource class {}', driver_class, resource_class)
    pkdc('slots available? {}', _slots_available(driver_class, resource_class))
    # TODO(e-carlin): this needs a lot of work    
    drivers = driver_class.resources[resource_class].drivers
    for request_index in range(_len_longest_requests_q(drivers)):
        for d in drivers:
            # there must be a request to execut
            if request_index < len(d.requests):
                r = d.requests[request_index]
                # the request must not already be executing
                if r.state != STATE_EXECUTION_PENDING:
                    continue
                # if the request is a _DATA_ACTION then there must be no others running
                if r.content.action in DATA_ACTIONS:
                    pkdp('***** checking if other data jobs running action={} r.jhash={}, len()={}', r.content.action, r.content.jhash, len(d.running_data_jobs))
                    if len(d.running_data_jobs) > 0:
                        continue

                # start agent if not started and slots available
                if not d.agent_started and _slots_available(driver_class, resource_class):
                        d.start_agent()
                        # TODO(e-carlin): maybe this should live within DriverBase start_agent()
                        driver_class.resources[resource_class].slots.in_use += 1
                # TODO(e-carlin): If r is a cancel and ther is no agent then???
                # TODO(e-carlin): If r is a cancel and the job is execution_pending
                # then delete from q and respond to server out of band about cancel
                # TODO(e-carlin): If there are no slots free one up
                #   - if the owner of a slot has no executing jobs then kill its
                #   agent. If the request q is empty remove from driver from drivers
                #   - use some starvation algo so that if someone has an agent
                #   and is sending a lot of jobs then after some number of jobs
                #   there agent should be killed an another user's agent started


                if r.content.action in DATA_ACTIONS:
                    assert r.content.run_dir not in d.running_data_jobs
                    d.running_data_jobs.add(r.content.compute_model_name)

                r.state = STATE_EXECUTING
                drivers.append(drivers.pop(drivers.index(d)))
                await d.requests_to_send_to_agent.put(r)


def _slots_available(driver_class, resource_class):
    s = driver_class.resources[resource_class].slots
    return s.in_use < s.total


def _len_longest_requests_q(drivers):
    m = 0
    for d in drivers:
        m = max(m, len(d.requests))
    return m


def _any_requests_executing(requests):
    for r in requests:
        if r.state == STATE_EXECUTING:
            return True
    return False