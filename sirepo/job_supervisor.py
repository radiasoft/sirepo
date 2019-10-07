# -*- coding: utf-8 -*-
"""TODO(e-carlin): Doc

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkcollections
from pykern import pkjson
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdc, pkdlog, pkdexc
from sirepo import driver, job
import aenum
import copy
import sirepo.driver
import sys
import tornado.locks

_DATA_ACTIONS = (job.ACTION_RUN_EXTRACT_JOB, job.ACTION_START_COMPUTE_JOB)

_OPERATOR_ACTIONS = (job.ACTION_CANCEL_JOB,)


class _RequestState(aenum.Enum):
    CHECK_STATUS = 'check_status'
    REPLY = 'reply'
    RUN = 'run'
    RUN_PENDING = 'run_pending'

_WAIT = (_RequestState.RUN_PENDING, _RequestState.CHECK_STATUS)


async def incoming(msg):
    run_scheduler(
        await globals()[f'incoming_{msg.handler.sr_req_type}'](msg),
    )


async def incoming_message(msg):
    d = sirepo.driver.get_instance(msg)
    a = msg.content.get('action')
    if a == job.ACTION_READY_FOR_WORK:
        return d
    if a == job.ACTION_ERROR:
        pkdlog('received error msg={}', job.LogFormatter(msg))
    r = _get_request_for_message(msg)
    r.set_response(msg.content)
    _remove_from_running_data_jobs(d, r, msg)
    return d


async def incoming_request(req):
    r = _Request(req)
    if r.content.action == job.ACTION_START_COMPUTE_JOB:
        res = await _run_compute_job_request(r)
    else:
        res = await r.get_reply()
    r.reply(res)
    return r._driver


def init():
    job.init()
    sirepo.driver.init()


def restart_requests(driver):
    for r in driver.requests:
        # TODO(e-carlin): Think more about this. If the kill was requested
        # maybe the jobs are running too long? If the kill wasn't requested
        # maybe the job can't be run and is what is causing the agent to
        # die?
        if r.state == _RequestState.RUN:
            r.state = _RequestState.RUN_PENDING


def run_scheduler(driver):
    try:
        pkdc('{}', driver)
        # TODO(e-carlin): complete. run status from runSimulation needs to be moved
        # into here before this will work
        # _handle_cancel_requests(
        #     driver_class.resources[resource_class].drivers)
        # TODO(e-carlin): This is the main component of the scheduler and needs
        # to be broken down and made more readable
        for d in driver.resources[driver.resource_class].drivers:
            for r in d.requests:
                a = r.content.action
                if r.state not in _WAIT or a in _DATA_ACTIONS and d.running_data_jobs:
                    continue
                # if the request is for status of a job pending in the q or in
                # running_data_jobs then reply out of band
                if a == job.ACTION_COMPUTE_JOB_STATUS:
                    j = _get_data_job_request(d, r.content.jid)
    #TODO(robnagler) why not reply in all cases if we have it?
                    if j and j.state in _WAIT:
                        r.state = _RequestState.REPLY
                        r.set_response(PKDict(status=job.Status.PENDING.value))
                        continue

                # start agent if not started and slots available
                if not d.is_started() and d.slots_available():
                    d.start(r)

                # TODO(e-carlin): If r is a cancel and there is no agent then???
                # rn nothing to do, just reply canceled
                # TODO(e-carlin): If r is a cancel and the job is run_pending
                # then delete from q and respond to server in band about cancel
                if d.is_started():
    #TODO(robnagler) how do we know which "r" is started?
                    _add_to_running_data_jobs(d, r)
                    r.state = _RequestState.RUN
                    drivers.append(drivers.pop(drivers.index(d)))
                    d.requests_to_send_to_agent.put_nowait(r)
    except Exception as e:
        pkdlog('exception={} driver={}', e, driver)
        pkdlog(pkdexc())
        # run_scheduler cannot throw exceptions


def terminate():
    sirepo.driver.terminate()


class _Request(PKDict):
    def __init__(self, req):
        self.content = req.content
        self.state = _RequestState.CHECK_STATUS if req.content.action == job.ACTION_START_COMPUTE_JOB \
            else _RequestState.RUN_PENDING
        self._handler = req.get('handler')
        self._response_received = tornado.locks.Event()
        self._response = None
        self._driver = sirepo.driver.get_class(self).enqueue_request(self)
        run_scheduler(self._driver)

    def __repr__(self):
        return 'state={}, content={}'.format(self.state, self.content)

    async def get_reply(self):
        await self._response_received.wait()
        self._driver.dequeue_request(self)
        self._driver = None
        return self._response

    def reply(self, reply):
        self._handler.write(reply)

    def reply_error(self):
        self._handler.send_error()

    def set_response(self, response):
        self._response = response
        self._response_received.set()

    def _requires_dependent_request(self):
        return


class _SupervisorRequest(_Request):
    def __init__(self, req, action):
        c = copy.deepcopy(req.content)
        c.action = action
        c.req_id = job.unique_key()
        super().__init__(PKDict(content=c))


def _add_to_running_data_jobs(driver, req):
    if req.content.action in _DATA_ACTIONS:
        assert req.content.jid not in driver.running_data_jobs
        driver.running_data_jobs.add(req.content.jid)


def _free_slots_if_needed(driver_class, resource_class):
    slot_needed = False
    for d in driver_class.resources[resource_class].drivers:
        if d.is_started() and len(d.requests) > 0  and not d.slots_available():
            slot_needed = True
            break
    if slot_needed:
        _try_to_free_slot(driver_class, resource_class)


def _get_data_job_request(driver, jid):
    for r in driver.requests:
        if r.content.action in _DATA_ACTIONS and r.content.jid is jid:
            return r
    return None


def _get_request_for_message(msg):
    d = sirepo.driver.get_instance(msg)
    for r in d.requests:
        if r.content.req_id == msg.content.req_id:
            return r
    raise RuntimeError(
        'req_id {} not found in requests {}'.format(
        msg.content.req_id,
        d.requests
    ))


def _len_longest_requests_q(drivers):
    m = 0
    for d in drivers:
        m = max(m, len(d.requests))
    return m


def _remove_from_running_data_jobs(driver, req, msg):
    # TODO(e-carlin): ugly
    a = req.content.action
    if (a == job.ACTION_COMPUTE_JOB_STATUS
        and job.Status.RUNNING.value != msg.content.status
        or a in (job.ACTION_RUN_EXTRACT_JOB, job.ACTION_CANCEL_JOB)
    ):
        driver.running_data_jobs.discard(req.content.jid)


# TODO(e-carlin): This isn't necessary right now. It was built to show the
# pathway of the supervisor adding requests to the q. When runStatus can
# be pulled out of job_api then this will actually become useful.
async def _run_compute_job_request(req):
    s = _SupervisorRequest(req, job.ACTION_COMPUTE_JOB_STATUS)
    r = await s.get_reply()
    if 'status' in r and r.status not in job.ALREADY_GOOD_STATUS:
        req.state = _RequestState.RUN_PENDING
        run_scheduler(req._driver)
        r = await req.get_reply()
    return r


def _send_kill_to_unknown_agent(msg):
    try:
        msg.handler.write_message(
            PKDict(action=job.ACTION_KILL, req_id=job.unique_key()),
        )
    except Exception as e:
        pkdlog('exception={} msg={}', e, job.LogFormatter(msg))


def _try_to_free_slot(driver_class, resource_class):
    for d in driver_class.resources[resource_class].drivers:
        if d.is_started() and len(d.requests) == 0 and len(d.running_data_jobs) == 0:
            pkdc('agent_id={} agent being terminated to free slot', d.agent_id)
#rn need to manage this lower down
            d.kill()
            d.resources[resource_class].drivers.remove(d)
            return
        # TODO(e-carlin): More cases. Ex:
        #   - if user has had an agent for a long time kill it when appropriate
        #   - if the owner of a slot has no executing jobs then terminate the
        #   agent but keep the driver around so the pending jobs will get run
        #   eventually
        #   - use a starvation algo so that if someone has an agent
        #   and is sending a lot of jobs then after some x (ex number of jobs,
        #   time, etc) their agent is killed and another user's agent started.
