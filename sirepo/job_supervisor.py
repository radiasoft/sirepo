# -*- coding: utf-8 -*-
"""TODO(e-carlin): Doc

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkcollections
from pykern.pkdebug import pkdp, pkdc, pkdlog, pkdexc
from sirepo import driver, job
import copy
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
    try:
        d = sirepo.driver.DriverBase.get_driver_for_agent(msg.content.agent_id)
    except KeyError:
        pkdlog('no known agent with id={}. Sending kill', msg.content.agent_id)
        _send_kill_to_uknown_agent(msg)
        return
    except AttributeError:
        pkdlog('msg={} did not contain agent_id', DebugRenderer(msg))
        return
    d.set_message_handler(msg.message_handler)
    a = msg.content.get('action')
    if a == job.ACTION_READY_FOR_WORK:
        run_scheduler(type(d), d.resource_class)
        return
    if a == job.ACTION_ERROR:
        pkdlog('received error from agent: {}', DebugRenderer(msg))
    try:
        r = _get_request_for_message(msg)
    except (KeyError, AttributeError):
        pkdlog(
            'Error no associated request for msg={} \n{}',
            DebugRenderer(msg),
            pkdexc()
        )
        return
    r.set_response(msg.content)
    _remove_from_running_data_jobs(d, r, msg)
    run_scheduler(type(d), d.resource_class)


async def incoming_request(req):
    r = _Request(req)
    if r.content.action == job.ACTION_START_COMPUTE_JOB:
        res = await _run_compute_job_request(r)
    else:
        res = await r.get_reply()
    r.reply(res)
    run_scheduler(
        sirepo.driver.DriverBase.get_driver_class(r),
        r.content.resource_class,
    )


# TODO(e-carlin): This isn't necessary right now. It was built to show the
# pathway of the supervisor adding requests to the q. When runStatus can
# be pulled out of job_api then this will actually become useful.
async def _run_compute_job_request(run_compute_job_req):
    run_status_req = _SupervisorRequest(
        run_compute_job_req,
        job.ACTION_COMPUTE_JOB_STATUS
    )
    res = await run_status_req.get_reply()
    already_good_status = [
        job.JobStatus.RUNNING,
        job.JobStatus.COMPLETED,
    ]
    if 'status' in res and res.status not in already_good_status:
        run_compute_job_req.waiting_on_dependent_request = False
        run_scheduler(
            sirepo.driver.DriverBase.get_driver_class(run_compute_job_req),
            run_compute_job_req.content.resource_class,
        )
        res = await run_compute_job_req.get_reply()
    return res


async def process_incoming(content, handler):
    try:
        pkdlog('{}: {}', handler.sr_req_type,  DebugRenderer(content))
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

                # if the request is for status of a job pending in the q or in
                # running_data_jobs then reply out of band
                if r.content.action == job.ACTION_COMPUTE_JOB_STATUS:
                    j = _get_data_job_request(d, r.content.jid)
                    if j and j.state == _STATE_RUN_PENDING:
                        r.state = _STATE_RUNNING
                        r.set_response(pkcollections.Dict(
                            status=job.JobStatus.PENDING.value,
                            )
                        )
                        continue

                # start agent if not started and slots available
                if not d.agent_started() and _slots_available(driver_class, resource_class):
                    d.start_agent(r)

                # TODO(e-carlin): If r is a cancel and ther is no agent then???
                # TODO(e-carlin): If r is a cancel and the job is execution_pending
                # then delete from q and respond to server out of band about cancel
                if d.agent_started():
                    _add_to_running_data_jobs(d, r)
                    r.state = _STATE_RUNNING
                    drivers.append(drivers.pop(drivers.index(d)))
                    d.requests_to_send_to_agent.put_nowait(r)


def _add_to_running_data_jobs(driver, req):
    if req.content.action in DATA_ACTIONS:
        assert req.content.jid not in driver.running_data_jobs
        driver.running_data_jobs.add(req.content.jid)


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


class DebugRenderer():
    def __init__(self, obj):
        self.obj = obj

    def __str__(self):
        o = self.obj
        if isinstance(o, pkcollections.Dict):
            return str(
                {x: (o[x] if x not in ['result', 'arg'] else '<snip>') for x in o}
            )
        raise AssertionError('unknown object to render: {}', o)


def _free_slots_if_needed(driver_class, resource_class):
    slot_needed = False
    for d in driver_class.resources[resource_class].drivers:
        if not d.agent_started() and len(d.requests) > 0 and not _slots_available(driver_class, resource_class):
            slot_needed = True
            break
    if slot_needed:
        _try_to_free_slot(driver_class, resource_class)


def _get_data_job_request(driver, jid):
    for r in driver.requests:
        if r.content.action in DATA_ACTIONS:
            if r.content.jid is jid:
                return r
    return None


def _get_request_for_message(msg):
    d = sirepo.driver.DriverBase.get_driver_for_agent(msg.content.agent_id)
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


def _remove_from_running_data_jobs(driver, req, msg):
    # TODO(e-carlin): ugly
    if req.content.action == job.ACTION_COMPUTE_JOB_STATUS:
        if msg.content.status != job.JobStatus.RUNNING.value:
            driver.running_data_jobs.discard(req.content.jid)
    elif req.content.action == job.ACTION_RUN_EXTRACT_JOB \
        or req.content.action == job.ACTION_CANCEL_JOB:
        driver.running_data_jobs.discard(req.content.jid)


class _Request():
    def __init__(self, req):
        self.state = _STATE_RUN_PENDING
        self.content = req.content
        self._request_handler = req.get('request_handler', None)
        self._response_received = tornado.locks.Event()
        self._response = None
        self.waiting_on_dependent_request = self._requires_dependent_request()
        driver.DriverBase.enqueue_request(self)
        run_scheduler(
            sirepo.driver.DriverBase.get_driver_class(self),
            self.content.resource_class,
        )

    def __repr__(self):
        return 'state={}, content={}'.format(self.state, self.content)

    async def get_reply(self):
        await self._response_received.wait()
        driver.DriverBase.dequeue_request(self)
        return self._response

    def reply(self, reply):
        self._request_handler.write(reply)

    def reply_error(self):
        self._request_handler.send_error()

    def set_response(self, response):
        self._response = response
        self._response_received.set()

    def _requires_dependent_request(self):
        return self.content.action == job.ACTION_START_COMPUTE_JOB


def _send_kill_to_uknown_agent(incoming_msg):
    try:
        incoming_msg.message_handler.write_message(
           pkcollections.Dict(
               action=job.ACTION_KILL,
               req_id=str(uuid.uuid4()),
            )
        )
    except Exception as e:
        pkdlog('Error: {}', e)


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
        # TODO(e-carlin): Fix this is a hack. If the parent request requires a
        # dependent req then when we call super() this will be set. This overrides
        # it with the action that is actually going to be for this request.
        self.waiting_on_dependent_request = self._requires_dependent_request()
        # TODO(e-carlin): Same hack as above
        run_scheduler(
            sirepo.driver.DriverBase.get_driver_class(self),
            self.content.resource_class,
        )


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
