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
import aenum
import copy
import sirepo.driver
import sirepo.job
import sys
import tornado.locks


_DATA_ACTIONS = (sirepo.job.ACTION_ANALYSIS, sirepo.job.ACTION_COMPUTE)

_OPERATOR_ACTIONS = (sirepo.job.ACTION_CANCEL,)


class _RequestState(aenum.Enum):
    CHECK_STATUS = 'check_status'
    REPLY = 'reply'
    RUN = 'run'
    RUN_PENDING = 'run_pending'

_WAIT = (_RequestState.RUN_PENDING, _RequestState.CHECK_STATUS)


class _Base(PKDict):

    async def do(self):
        await self._do()


# async def incoming(msg):
#     run_scheduler(
#         await globals()[f'incoming_{msg.handler.sr_req_type}'](msg),
#     )


# async def incoming_message(msg):
#     d = sirepo.driver.get_instance(msg)
#     a = msg.content.get('action')
#     if a == sirepo.job.ACTION_READY_FOR_WORK:
#         return d
#     if a == sirepo.job.ACTION_ERROR:
#         pkdlog('received error msg={}', sirepo.job.LogFormatter(msg))
#     r = _get_request_for_message(msg)
#     r.set_response(msg.content)
#     _remove_from_running_data_jobs(d, r, msg)
#     return d


# async def incoming_request(req):
#     r = ServerReq(req)
#     d = r._driver
#     if r.content.action == sirepo.job.ACTION_COMPUTE:
#         res = await _run_compute_job_request(r)
#     else:
#         res = await r.get_reply()
#     r.reply(res)
#     return d


def init():
    sirepo.job.init()
    sirepo.driver.init()


def restart_requests(driver):
    for r in driver.requests:
        # TODO(e-carlin): Think more about this. If the kill was requested
        # maybe the jobs are running too long? If the kill wasn't requested
        # maybe the job can't be run and is what is causing the agent to
        # die?
        if r.state == _RequestState.RUN:
            r.state = _RequestState.RUN_PENDING


def run_scheduler(kind):
    try:
        pkdc('kind={}', kind)
        for j in _Jobs.jobs.get(kind, []):
            if not j.ops:
                continue

            o = j.ops[0]
            r = j.requests[0]

#         # TODO(e-carlin): complete. run status from runSimulation needs to be moved
#         # into here before this will work
#         # _handle_cancel_requests(
#         #     driver_class.resources[resource_class].drivers)
#         # TODO(e-carlin): This is the main component of the scheduler and needs
#         # to be broken down and made more readable
#         drivers = driver.resources[driver.resource_class].drivers
#         for d in drivers:
#             if not d.requests:
#                 continue
#             r = d.requests[0]
#             a = r.content.action
#             if r.state not in _WAIT or a in _DATA_ACTIONS and d.running_data_jobs:
#                 continue
#             # if the request is for status of a job pending in the q or in
#             # running_data_jobs then reply out of band
#             if a == sirepo.job.ACTION_STATUS:
#                 j = _get_data_job_request(d, r.content.jid)
# #TODO(robnagler) why not reply in all cases if we have it?
#                 if j and j.state in _WAIT:
#                     r.state = _RequestState.REPLY
#                     r.set_response(PKDict(status=sirepo.job.Status.PENDING.value))
#                     continue

#             # start agent if not started and slots available
#             if not d.is_started() and d.slots_available():
#                 d.start(r)

#             # TODO(e-carlin): If r is a cancel and there is no agent then???
#             # rn nothing to do, just reply canceled
#             # TODO(e-carlin): If r is a cancel and the job is run_pending
#             # then delete from q and respond to server in band about cancel
#             if d.is_started():
# #TODO(robnagler) how do we know which "r" is started?
#                 _add_to_running_data_jobs(d, r)
#                 r.state = _RequestState.RUN
#                 drivers.append(drivers.pop(drivers.index(d)))
#                 d.requests_to_send_to_agent.put_nowait(r)
    except Exception as e:
        pkdlog('exception={} driver={}', e, driver)
        pkdlog(pkdexc())
        # run_scheduler cannot throw exceptions


def terminate():
    sirepo.driver.terminate()


class _Job(PKDict):

    instances = PKDict()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'jid' not in self:
            self.jid = self._jid_for_req(self.req)

    @classmethod
    async def get_compute_status(cls, req):
        #TODO(robnagler) deal with non-in-memory job state (db?)
        self = cls.instances.get(cls._jid(req))
        if not self:
            self = cls(req=req)
        return await sirepo.driver.get_compute_status(self)

    def _jid_for_req(cls, req):
        c = req.content
        if c.api in ('api_runStatus', 'api_runCancel', 'api_runSimulation')
            return c.compute_jid
        if c.api in ('api_simulationFrame',):
            return c.analysis_jid
        raise AssertionError('unknown api={} req={}', c.api, req)


class ServerReq(_Base):
    def __init__(self, req):
        c = req.content
        self.content = c
        self.state = _RequestState.CHECK_STATUS if req.content.action == sirepo.job.ACTION_COMPUTE \
            else _RequestState.RUN_PENDING
        self._handler = req.get('handler')
        self._response_received = tornado.locks.Event()
        self._response = None
        self._action = c.action
        self.uid = c.uid
        self._resource_class = sirepo.job
        self.driver_kind = sirepo.driver.get_kind(self)
        self._my_queue = self.instances.setdefault(
            self._driver_kind,
            PKDict(),
        ).setdefault(
            self._uid,
            PKDict(),
        )

    async def _do(self):
        c = self.content
        if c.api == 'api_runStatus':
            self._handler.write(await Job.get_compute_status(self))
            return



def _simulation_run_status_job_supervisor(data, quiet=False):
    """Look for simulation status and output

    Args:
        data (dict): request
        quiet (bool): don't write errors to log

    Returns:
        dict: status response
    """
    try:
        b = PKDict(
            run_dir=simulation_db.simulation_run_dir(data),
            jhash=template_common.report_parameters_hash(data),
            jid=simulation_db.job_id(data),
            parallel=simulation_db.is_parallel(data),
        )
        rep = simulation_db.report_info(data)
        res = PKDict(state=status.value)

        status = job.compute_job_status(b)
        is_running = status is sirepo.job.Status.RUNNING



bla bla


        pkdc(
            'jid={} is_running={} state={}',
            rep.job_id,
            is_running,
            status,
        )
        if not is_running:
            if status is not sirepo.job.Status.MISSING:
                res, err = job_api.run_extract_job(b.setdefault(cmd='result'))
                if err:
                    return http_reply.subprocess_error(err, 'error in read_result', b.run_dir)
        res['parametersChanged'] = rep.parameters_changed
        if res['parametersChanged']:
            pkdlog(
                '{}: parametersChanged=True req_hash={} cached_hash={}',
                rep.job_id,
                rep.req_hash,
                rep.cached_hash,
            )
        #TODO(robnagler) verify serial number to see what's newer
        res.setdefault('startTime', _mtime_or_now(rep.input_file))
        res.setdefault('lastUpdateTime', _mtime_or_now(rep.run_dir))
        res.setdefault('elapsedTime', res['lastUpdateTime'] - res['startTime'])
also return computeHash for simulationFrame
        if is_running:
            res['nextRequestSeconds'] = simulation_db.poll_seconds(rep.cached_data)
            res['nextRequest'] = {
                'report': rep.model_name,
                'reportParametersHash': rep.cached_hash,
                'simulationId': rep.cached_data['simulationId'],
                'simulationType': rep.cached_data['simulationType'],
            }
        pkdc(
            '{}: processing={} state={} cache_hit={} cached_hash={} data_hash={}',
            rep.job_id,
            is_running,
            res['state'],
            rep.cache_hit,
            rep.cached_hash,
            rep.req_hash,
        )
    except Exception:
        return http_reply.subprocess_error(pkdexc(), quiet=quiet)
    return res

def _mtime_or_now(path):
    """mtime for path if exists else time.time()

    Args:
        path (py.path):

    Returns:
        int: modification time
    """
    return int(path.mtime() if path.exists() else time.time())


def compute():
    has to call report_info (not status)
    if first time to create job
    status = job.compute_job_status(b)
#TODO(robnagler) move into supervisor & agent
    if status not in sirepo.job.ALREADY_GOOD_STATUS:
        b.req_id = sirepo.job.unique_key()
        job.start_compute_job(
            body=b.update(
                cmd=cmd,
                sim_id=data.simulationId,
                input_dir=d,
            ),
        )
    res = _simulation_run_status_job_supervisor(data, quiet=True)
    return http_reply.gen_json(res)

def cancel():
    # Always true from the client's perspective
    return http_reply.gen_json(PKDict(state='canceled'))


    def __repr__(self):
        return 'state={}, content={}'.format(self.state, self.content)

    def enqueue(self):
        # type of request matters:
        if self.content.action in (sirepo.job.ACTION_CANCEL, sirepo.job.ACTION_STATUS):
            self._my_queue.insert(0, self)
        else:
            self._my_queue.append(self)
        for d in cls.resources[req.content.resource_class].drivers:
            if d.uid == req.content.uid:
                break
        else:
            d = cls(
                uid=req.content.uid,
                resource_class=req.content.resource_class,
                supervisor_uri=cfg.supervisor_uri,
            )
            d.resources[d.resource_class].drivers.append(d)
            cls.instances[d.agent_id] = d
        d.requests.append(req)
        return d

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

class _Job():
    jobs = PKDict()

    def __init__(self, request):
        self.requests = [request]
        self.ops = []
        self.kind = request.kind
        self.compute_jid = requests.content.compute_jid

    @classmethod
    async def status(cls, request):
        j = cls._get_job(request)
        j.requests.append(request)
        await j.get_status()
        return

    @classmethod
    def _get_job(cls, request):
        """
        jobs = {
            kind: [
                user: {
                    uid: xxx,
                    jobs: [job1, job2]
                ]
            }
        }
        """
        if request.kind in jobs:
            for u in jobs[request.kind]:
                for j in u.jobs:
                    if j.compute_jid == request.content.compute_jid:
                        return j
        j = _Job(request)
        jobs.setdefault(request.kind, [])
        for u in jobs[request.kind]:
            if u.uid == request.uid:
                u.jobs.append()
                return
        jobs[request.kind][request.uid].uid = request.uid
        jobs[request.kind][request.uid].jobs = [j]
        return j

    async def get_status(self):
        # TODO(e-carlin): Cache values and if present read from there
        o = _Op.get_status(self)
        self.ops.append(o)
        run_scheduler(self.kind)
        return await o.get_result()



class _Op():

    def __init__(self):
        self._result_set = tornado.locks.Event()
        self._result = None

    async def get_result(self):
        await self.result_set.wait()
        return self._result

    @classmethod
    def get_status(cls, job):
        o = _Op()


# class _SupervisorRequest(ServerReq):
#     def __init__(self, req, action):
#         c = copy.deepcopy(req.content)
#         c.action = action
#         c.req_id = sirepo.job.unique_key()
#         super().__init__(PKDict(content=c))


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
    if (a == sirepo.job.ACTION_STATUS
        and sirepo.job.Status.RUNNING.value != msg.content.status
        or a in (sirepo.job.ACTION_ANALYSIS, sirepo.job.ACTION_CANCEL)
    ):
        driver.running_data_jobs.discard(req.content.jid)


# TODO(e-carlin): This isn't necessary right now. It was built to show the
# pathway of the supervisor adding requests to the q. When runStatus can
# be pulled out of job_api then this will actually become useful.
async def _run_compute_job_request(req):
    s = _SupervisorRequest(req, sirepo.job.ACTION_STATUS)
    r = await s.get_reply()
    if 'status' in r and r.status not in sirepo.job.ALREADY_GOOD_STATUS:
        req.state = _RequestState.RUN_PENDING
        run_scheduler(req._driver)
        r = await req.get_reply()
    return r


def _send_kill_to_unknown_agent(msg):
    try:
        msg.handler.write_message(
            PKDict(action=sirepo.job.ACTION_KILL, req_id=sirepo.job.unique_key()),
        )
    except Exception as e:
        pkdlog('exception={} msg={}', e, sirepo.job.LogFormatter(msg))


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
