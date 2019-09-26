# -*- coding: utf-8 -*-
"""TODO(e-carlin): Doc

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkconfig, pkcollections
from pykern.pkdebug import pkdp, pkdc, pkdlog
from sirepo import driver, job
from sirepo import job
import importlib
import sirepo.driver
import tornado.locks
import uuid

_STATE_RUN_PENDING = 'run_pending' 
_STATE_RUNNING = 'running'

DATA_ACTIONS = [
    job.ACTION_RUN_EXTRACT_JOB,
    job.ACTION_START_COMPUTE_JOB,
]

_OPERATOR_ACTIONS = [
    job.ACTION_CANCEL_JOB,
]

def _get_request_for_message(msg):
    d = sirepo.driver.DriverBase.driver_for_agent[msg.content.agent_id]
    for r in d.requests:
        if r.content.req_id == msg.content.req_id:
            return r

    raise AssertionError(
        'req_id {} not found in requests {}'.format(
        msg.content.req_id,
        d.requests
    ))

def _remove_request(msg):
    sirepo.driver.DriverBase.driver_for_agent[msg.content.agent_id].requests.remove(
        _get_request_for_message(msg)
    )

async def incoming_message(msg):
    d = sirepo.driver.DriverBase.driver_for_agent[msg.content.agent_id]
    if not d.message_handler_set.is_set():
        d.set_message_handler(msg.message_handler)

    a = msg.content.get('action')
    if a == job.ACTION_READY_FOR_WORK:
        run_scheduler(type(d), d.resource_class)
        return
    elif a == 'protocol_error':
        # TODO(e-carlin): Handle more. If msg has a req_id we should
        # likely resend the request
        pkdlog('Error: {}', msg)
        run_scheduler(type(d), d.resource_class)
        return

    r = _get_request_for_message(msg)
    r.reply(msg.content)
    _remove_request(msg) 

    # TODO(e-carlin): This is quite ugly. 
    if r.content.action == job.ACTION_COMPUTE_JOB_STATUS:
        if msg.content.status != job.JobStatus.RUNNING.value:
            d.running_data_jobs.discard(r.content.jid)
    elif r.content.action == job.ACTION_RUN_EXTRACT_JOB:
        d.running_data_jobs.discard(r.content.jid)
    elif r.content.action == job.ACTION_CANCEL_JOB:
        d.running_data_jobs.discard(r.content.jid)

    run_scheduler(type(d), d.resource_class)

async def incoming_request(req):
    r = _Request(req)
    dc = _get_driver_class(req)

    for d in dc.resources[r.content.resource_class].drivers:
        if d.uid == r.content.uid:
            d.requests.append(r)
            break
    else:
        d = dc(
            r.content.uid,
            r.content.resource_class
        )
        d.requests.append(r)
        dc.resources[r.content.resource_class].drivers.append(d)
        sirepo.driver.DriverBase.driver_for_agent[d.agent_id] = d

    run_scheduler(dc, req.content.resource_class)
    await r.request_reply_was_sent.wait()


def _get_driver_class(request):
    # TODO(e-carlin): Handle nersc and sbatch. Request will need to be parsed
    t = 'docker' if pkconfig.channel_in('alpha', 'beta', 'prod') else 'local'
    m = importlib.import_module(
        f'sirepo.driver.{t}'
    )
    return getattr(m, f'{t.capitalize()}Driver')


def run_scheduler(driver_class, resource_class):
    pkdc(
        'supervisor running for driver {} and resource class {}. Slots available={}',
        driver_class,
        resource_class,
        _slots_available(driver_class, resource_class),
    )
    # TODO(e-carlin): complete
    # _handle_cancel_requests(
    #     driver_class.resources[resource_class].drivers)
    drivers = driver_class.resources[resource_class].drivers
    for request_index in range(_len_longest_requests_q(drivers)):
        for d in drivers:
            _free_slots_if_needed(driver_class, resource_class)
            # there must be a request to execute
            if request_index < len(d.requests):
                r = d.requests[request_index]
                # the request must not already be executing
                if r.state != _STATE_RUN_PENDING:
                    continue
                # if the request is a _DATA_ACTION then there must be no others running
                if r.content.action in DATA_ACTIONS and len(d.running_data_jobs) > 0:
                    continue

                # start agent if not started and slots available
                if not d.agent_started() and _slots_available(driver_class, resource_class):
                    d.start_agent(r)

                # TODO(e-carlin): If r is a cancel and ther is no agent then???
                # TODO(e-carlin): If r is a cancel and the job is execution_pending
                # then delete from q and respond to server out of band about cancel

                if d.agent_started():
                    if d.agent_started() and r.content.action in DATA_ACTIONS:
                        assert r.content.jid not in d.running_data_jobs
                        d.running_data_jobs.add(r.content.jid)
                    r.state = _STATE_RUNNING
                    drivers.append(drivers.pop(drivers.index(d)))
                    d.requests_to_send_to_agent.put_nowait(r)


def _handle_cancel_requests(drivers):
    for d in drivers:
        for r in d.requests:
            if r.content.action == job.ACTION_CANCEL_JOB:
                _cancel_pending_job(d, r)


def _cancel_pending_job(driver, cancel_req):
    def _reply_job_canceled(r, requests):
        r.reply({
            'status': job.JobStatus.CANCELED.value,
            'req_id': r.content.req_id,
        })
        requests.remove(r)
    def _get_compute_request(jid):
        for r in driver.requests:
            if r.content.action == job.ACTION_START_COMPUTE_JOB and r.content.jid == jid:
                return r
        return None

    compute_req = _get_compute_request(cancel_req.content.jid)
    if compute_req is None:
        for r in driver.requests:
            if r.content.jid == cancel_req.content.jid:
                _reply_job_canceled(r, driver.requests)
        cancel_req.reply({'status': job.JobStatus.CANCELED.value})
        driver.requests.remove(cancel_req)

    elif compute_req.state == _STATE_RUN_PENDING:
        pkdlog('compute_req={}', compute_req)
        _reply_job_canceled(compute_req, driver.requests)

        cancel_req.reply({'status': job.JobStatus.CANCELED.value})
        driver.requests.remove(cancel_req)


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
        if not d.agent_started() and len(d.requests) > 0 and not _slots_available(driver_class, resource_class):
            slot_needed = True
            break
    if slot_needed:
        _try_to_free_slot(driver_class, resource_class)


def _try_to_free_slot(driver_class, resource_class):
    for d in driver_class.resources[resource_class].drivers:
        if d.agent_started() and len(d.requests) == 0 and len(d.running_data_jobs) == 0:
            pkdc('agent_id={} agent being terminated to free slot', d.agent_id)
            d.kill_agent()
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


class _Request():
    def __init__(self, request):
        self.content = request.content
        self.request_reply_was_sent = tornado.locks.Event()
        self.request_handler = request.request_handler
        self.state = _STATE_RUN_PENDING

    def reply(self, content):
        self.request_handler.write(content)
        self.request_reply_was_sent.set()

    def reply_error(self):
        self.request_handler.send_error()
