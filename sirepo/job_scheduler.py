# -*- coding: utf-8 -*-
"""TODO(e-carlin): Doc

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkdebug import pkdp, pkdc
from sirepo import driver, job
import uuid

STATE_RUN_PENDING = 'run_pending'
_STATE_RUNNING = 'running'

DATA_ACTIONS = [
    job.ACTION_RUN_EXTRACT_JOB,
    job.ACTION_START_COMPUTE_JOB,
]

_OPERATOR_ACTIONS = [
    job.ACTION_CANCEL_JOB,
]


async def run(driver_class, resource_class):
    pkdc(
        'scheduler running for driver {} and resource class {}. Slots available={}',
        driver_class,
        resource_class,
        _slots_available(driver_class, resource_class),
    )
    # TODO(e-carlin): complete
    # _remove_canceled_pending_jobs(
    #     driver_class.resources[resource_class].drivers)
    drivers = driver_class.resources[resource_class].drivers
    for request_index in range(_len_longest_requests_q(drivers)):
        for d in drivers:
            _free_slots_if_needed(driver_class, resource_class)
            # there must be a request to execute
            if request_index < len(d.requests):
                r = d.requests[request_index]
                # the request must not already be executing
                if r.state != STATE_RUN_PENDING:
                    continue
                # if the request is a _DATA_ACTION then there must be no others running
                if r.content.action in DATA_ACTIONS and len(d.running_data_jobs) > 0:
                    continue

                # start agent if not started and slots available
                if not d.agent_started and _slots_available(driver_class, resource_class):
                    d.start_agent()
                    # TODO(e-carlin): maybe this should live within DriverBase start_agent()
                    driver_class.resources[resource_class].slots.in_use += 1

                # TODO(e-carlin): If r is a cancel and ther is no agent then???
                # TODO(e-carlin): If r is a cancel and the job is execution_pending
                # then delete from q and respond to server out of band about cancel

                if d.agent_started:
                    if d.agent_started and r.content.action in DATA_ACTIONS:
                        assert r.content.compute_model_name not in d.running_data_jobs
                        d.running_data_jobs.add(r.content.compute_model_name)
                    r.state = _STATE_RUNNING
                    drivers.append(drivers.pop(drivers.index(d)))
                    await d.requests_to_send_to_agent.put(r)


def _remove_canceled_pending_jobs(drivers):
    for d in drivers:
        for r in d.requests:
            if r.content.action == job.ACTION_CANCEL_JOB:
                _cancel_pending_jobs(driver, r)


def _cancel_pending_jobs(driver, cancel_req):
    job_running = False
    for r in driver.requests:
        if r.content.compute_model_name == cancel_req.content.compute_model_name:
            if r.state == STATE_RUN_PENDING:
                # remove the req
                continue
            job_running = True
    if not job_running:
        # remove the cancel_req
        pass


def _slots_available(driver_class, resource_class):
    s = driver_class.resources[resource_class].slots
    return s.in_use < s.total


def _len_longest_requests_q(drivers):
    m = 0
    for d in drivers:
        m = max(m, len(d.requests))
    return m


def _free_slots_if_needed(driver_class, resource_class):
    slot_needed = False
    for d in driver_class.resources[resource_class].drivers:
        if not d.agent_started and len(d.requests) > 0 and not _slots_available(driver_class, resource_class):
            slot_needed = True
            break
    if slot_needed:
        _try_to_free_slot(driver_class, resource_class)


def _try_to_free_slot(driver_class, resource_class):
    for d in driver_class.resources[resource_class].drivers:
        if d.agent_started and len(d.requests) == 0 and len(d.running_data_jobs) == 0:
            pkdc('agent_id={} agent being terminated to free slot', d.agent_id)
            d.terminate_agent()
            driver_class.resources[resource_class].slots.in_use -= 1
            driver_class.resources[resource_class].drivers.remove(d)
            return
        # TODO(e-carlin): More cases. Ex:
        #   - if user has had an agent for a long time kill it when appropriate
        #   - if the owner of a slot has no executing jobs then terminate the
        #   agent but keep the driver around so the pending jobs will get run
        #   eventually
        #   - use a starvation algo so that if someone has an agent
        #   and is sending a lot of jobs then after some x (ex number of jobs,
        #   time, etc) their agent is killed and another user's agent started.
