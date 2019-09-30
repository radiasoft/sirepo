# -*- coding: utf-8 -*-
"""TODO(e-carlin): Doc

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkconfig, pkcollections
from pykern.pkdebug import pkdp, pkdc, pkdlog, pkdexc
from sirepo import driver, job
from sirepo import job
import copy
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


async def incoming_message(msg):
    d = sirepo.driver.DriverBase.driver_for_agent[msg.content.agent_id]
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
    _remove_request(msg) 
    if type(r) == _SupervisorRequest:
        r.result = msg
        r.request_reply_received.set()
        return
    r.reply(msg.content)
    # TODO(e-carlin): ugly
    if r.content.action == job.ACTION_COMPUTE_JOB_STATUS:
        if msg.content.status != job.JobStatus.RUNNING.value:
            d.running_data_jobs.discard(r.content.jid)
    elif r.content.action == job.ACTION_RUN_EXTRACT_JOB:
        d.running_data_jobs.discard(r.content.jid)
    elif r.content.action == job.ACTION_CANCEL_JOB:
        d.running_data_jobs.discard(r.content.jid)
    run_scheduler(type(d), d.resource_class)


async def incoming_request(req):
    """
    TODO(e-carlin): Instead of wait on request_reply_was_sent or depends_on_another_request
    just wait on a function that returns the results of the request. Then 
    reply to the request here instead of replying elsewhere.
    Hmm on second thought, a downside to replying here is when there is
    an error by replying elsewhwere the code that handles errors can reply
    to the error there and cleanup after itself which might be easier. It makes
    it easier to reply and reduces the if else's. We could use golang style
    tuples and do if err ... to get around this.

    r = _ServerRequest(req)
    driver.DriverBase.enqueue_request(r)
    if r.depends_on_another_request():
        pkdc('r={} depends on another request', r)
        r.waiting_on_dependent_request = True
        res, err = _run_dependent_request(r)
        if err:
            r.reply_error(err)
            run_scheduler(
                sirepo.driver.DriverBase.get_driver_class(r),
                r.content.resource_class,
            )
            # TODO(e-carlin): Who does cleanup of state? Us or where the error
            # was first encountered?
            return
        r.waiting_on_dependent_request = False
    run_scheduler(
        sirepo.driver.DriverBase.get_driver_class(r),
        r.content.resource_class,
    )
    res, err = await r.run()
    if err:
        r.reply_error(err)
    r.reply(res)
    """

    r = _ServerRequest(req)
    driver.DriverBase.enqueue_request(r)
    if r.depends_on_another_request():
        pkdc('r={} depends on another request', r)
        r.waiting_on_dependent_request = True
        await _run_dependent_request(r)
        r.waiting_on_dependent_request = False
    run_scheduler(
        sirepo.driver.DriverBase.get_driver_class(r),
        r.content.resource_class,
    )
    await r.request_reply_was_sent.wait()


async def process_incoming(content, handler):
    try:
        pkdlog('{}: {}', handler.sr_req_type,  _DebugRenderer(content))
        await globals()[f'incoming_{handler.sr_req_type}'](
            pkcollections.Dict({
                f'{handler.sr_req_type}_handler': handler,
                'content': content,
            })
        )
    except Exception as e:
        pkdlog('Error: {}', e)
        pkdlog(pkdexc())


def run_scheduler(driver_class, resource_class):
    pkdc(
        'driver_class={}, resource_class={}, slots_available={}',
        driver_class,
        resource_class,
        _slots_available(driver_class, resource_class),
    )
    # TODO(e-carlin): complete. run status from runSimulation needs to be moved
    # into here before this will work
    # _handle_cancel_requests(
    #     driver_class.resources[resource_class].drivers)
    # TODO(e-carlin): This is the main component of the scheduler and needs
    # to be broken down and made more readable
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

                if r.waiting_on_dependent_request:
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


class _DebugRenderer():
    def __init__(self, obj):
        self.obj = obj

    def __str__(self):
        o = self.obj
        if isinstance(o, pkcollections.Dict):
            return str({x: o[x] for x in o if x not in ['result', 'arg']})
        raise AssertionError('unknown object to render: {}', o)


def _free_slots_if_needed(driver_class, resource_class):
    slot_needed = False
    for d in driver_class.resources[resource_class].drivers:
        if not d.agent_started() and len(d.requests) > 0 and not _slots_available(driver_class, resource_class):
            slot_needed = True
            break
    if slot_needed:
        _try_to_free_slot(driver_class, resource_class)


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


def _handle_cancel_requests(drivers):
    for d in drivers:
        for r in d.requests:
            if r.content.action == job.ACTION_CANCEL_JOB:
                _cancel_pending_job(d, r)


def _len_longest_requests_q(drivers):
    m = 0
    for d in drivers:
        m = max(m, len(d.requests))
    return m


def _remove_request(msg):
    sirepo.driver.DriverBase.driver_for_agent[msg.content.agent_id].requests.remove(
        _get_request_for_message(msg)
    )

class _Request():
    def __init__(self, req):
        self.state = _STATE_RUN_PENDING
        self.waiting_on_dependent_request = False
        self.content = req.content

    def depends_on_another_request(self):
        # TODO(e-carlin): What requests will need another request run before?
        # runSimulation is one. What else?
        return self.content.action == job.ACTION_START_COMPUTE_JOB

    def __repr__(self):
        return 'state={}, content={}'.format(self.state, self.content)


async def _run_dependent_request(parent_req):
    r = _SupervisorRequest(parent_req, job.ACTION_COMPUTE_JOB_STATUS)
    sirepo.driver.DriverBase.enqueue_request(r)
    run_scheduler(
        sirepo.driver.DriverBase.get_driver_class(r),
        r.content.resource_class,
    )
    await r.request_reply_received.wait()


class _ServerRequest(_Request):
    def __init__(self, req):
        super(_ServerRequest, self).__init__(req)
        self.request_reply_was_sent = tornado.locks.Event()
        self.request_handler = req.request_handler

    def reply(self, content):
        self.request_handler.write(content)
        self.request_reply_was_sent.set()

    def reply_error(self):
        self.request_handler.send_error()


def _slots_available(driver_class, resource_class):
    s = driver_class.resources[resource_class].slots
    return len(s.in_use) < s.total


class _SupervisorRequest(_Request):
    def __init__(self, parent_req, action):
        super(_SupervisorRequest, self).__init__(
            pkcollections.Dict(
                content=copy.deepcopy(parent_req.content)
            )
        )
        self.content.action = action
        self.content.req_id = str(uuid.uuid4())
        self.request_reply_received = tornado.locks.Event() # TODO(e-carlin): Try and find a common name with request_reply_was_sent. Maybe just on_reply?
        self.result = None


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
