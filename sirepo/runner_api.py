# -*- coding: utf-8 -*-
u"""Entry points for runner (v1)

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkjson
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp, pkdpretty
import pykern.pkio
from sirepo import api_perm
from sirepo import http_reply
from sirepo import http_request
from sirepo import runner
from sirepo import simulation_db
from sirepo.template import template_common
import datetime
import flask
import hashlib
import inspect
import sirepo.sim_data
import sirepo.template
import time

#: What is_running?
_RUN_STATES = ('pending', 'running')


@api_perm.require_user
def api_downloadDataFile(simulation_type, simulation_id, model, frame, suffix=None):
#TODO(robnagler) validate suffix and frame
    req = http_request.parse_params(
        id=simulation_id,
        model=model,
        type=simulation_type,
    )
    f, c, t = sirepo.template.import_module(req.type).get_data_file(
        simulation_db.simulation_run_dir(req.req_data),
        req.model,
        int(frame),
        options=req.req_data.copy().update(suffix=suffix),
    )
    return http_reply.gen_file_as_attachment(c, f, t)


@api_perm.require_user
def api_runCancel():
    jid = None
    try:
        req = http_request.parse_post(id=True, model=True)
        jid = req.sim_data.parse_jid(req.req_data)
        # TODO(robnagler) need to have a way of listing jobs
        # Don't bother with cache_hit check. We don't have any way of canceling
        # if the parameters don't match so for now, always kill.
        #TODO(robnagler) mutex required
        if runner.job_is_processing(jid):
            run_dir = simulation_db.simulation_run_dir(req.req_data)
            # Write first, since results are write once, and we want to
            # indicate the cancel instead of the termination error that
            # will happen as a result of the kill.
            try:
                simulation_db.write_result({'state': 'canceled'}, run_dir=run_dir)
            except Exception as e:
                if not pykern.pkio.exception_is_not_found(e):
                    raise
                # else: run_dir may have been deleted
            runner.job_kill(jid)
            # TODO(robnagler) should really be inside the template (t.cancel_simulation()?)
            # the last frame file may not be finished, remove it
            t = sirepo.template.import_module(req.req_data)
            if hasattr(t, 'remove_last_frame'):
                t.remove_last_frame(run_dir)
    except Exception as e:
        pkdlog('ignoring exception={} jid={} stack={}', e, jid, pkdexc())
    # Always true from the client's perspective
    return http_reply.gen_json({'state': 'canceled'})


@api_perm.require_user
def api_runSimulation():
    req = http_request.parse_post(id=True, model=True, fixup_old_data=True)
    res = _simulation_run_status(req, quiet=True)
    if (
        (
            not res['state'] in _RUN_STATES
            and (res['state'] != 'completed' or req.req_data.get('forceRun', False))
        ) or res.get('parametersChanged', True)
    ):
        try:
            _start_simulation(req.req_data)
        except runner.Collision:
            pkdlog('{}: runner.Collision, ignoring start', _reqd(req).jid)
        res = _simulation_run_status(req)
    return http_reply.gen_json(res)


@api_perm.require_user
def api_runStatus():
    return http_reply.gen_json(
        _simulation_run_status(
            http_request.parse_post(id=True, model=True),
        ),
    )


@api_perm.require_user
def api_simulationFrame(frame_id):
    return template_common.sim_frame(
        frame_id,
        lambda a: template_common.sim_frame_dispatch(a),
    )


def init_apis(*args, **kwargs):
    pass


def _mtime_or_now(path):
    """mtime for path if exists else time.time()

    Args:
        path (py.path):

    Returns:
        int: modification time
    """
    return int(path.mtime() if path.exists() else time.time())


def _read_status(run_dir):
    """Read status from simulation dir

    Args:
        run_dir (py.path): where to read
    """
    try:
        return pykern.pkio.read_text(run_dir.join(sirepo.job.RUNNER_STATUS_FILE))
    except Exception as e:
        if pykern.pkio.exception_is_not_found(e):
            # simulation may never have been run
            return 'stopped'
        return 'error'


def _reqd(req):
    """Read the run_dir and return cached_data.

    Only a hit if the models between data and cache match exactly. Otherwise,
    return cached data if it's there and valid.

    Args:
        req (dict): parsed simulation data

    Returns:
        Dict: report parameters and hashes
    """
    res = PKDict(cache_hit=False,
        cached_data=None,
        cached_hash=None,
        parameters_changed=False,
        run_dir=simulation_db.simulation_run_dir(req.req_data),
        sim_data=req.sim_data,
    )
    res.pkupdate(
        input_file=simulation_db.json_filename(
            template_common.INPUT_BASE_NAME,
            res.run_dir,
        ),
        is_parallel=res.sim_data.is_parallel(req.req_data),
        jid=res.sim_data.parse_jid(req.req_data),
        job_status=_read_status(res.run_dir),
        model_name=res.sim_data.parse_model(req.req_data.report),
        req_hash=(
            req.req_data.get('computeJobHash')
            or res.sim_data.compute_job_hash(req.req_data)
        ),
    )
    if not res.run_dir.check():
        return res
    try:
        c = simulation_db.read_json(res.input_file)
    except Exception as e:
        if pykern.pkio.exception_is_not_found(e):
            return res
        raise
    res.cached_data = c
    # backwards compatibility for old runs that don't have computeJobCacheKey
    res.cached_hash = c.models.pksetdefault(
        computeJobCacheKey=lambda: PKDict(
            computeJobHash=res.sim_data.compute_job_hash(c),
            computeJobSerial=int(res.input_file.mtime()),
        ),
    ).computeJobCacheKey.computeJobHash
    if res.req_hash == res.cached_hash:
        res.cache_hit = True
        return res
    res.parameters_changed = True
    return res



def _simulation_run_status(req, quiet=False):
    """Look for simulation status and output

    Args:
        req (dict): parsed simulation data
        quiet (bool): don't write errors to log

    Returns:
        dict: status response
    """
    reqd = _reqd(req)
    in_run_simulation = 'models' in req.req_data
    if in_run_simulation:
        req.req_data.models.computeJobCacheKey = PKDict(
            computeJobHash=reqd.req_hash,
        )
    is_processing = runner.job_is_processing(reqd.jid)
    is_running = reqd.job_status in _RUN_STATES
    res = PKDict(state=reqd.job_status)
    pkdc(
        '{}: is_processing={} is_running={} state={} cached_data={}',
        reqd.jid,
        is_processing,
        is_running,
        reqd.job_status,
        bool(reqd.cached_data),
    )
    if is_processing and not is_running:
        runner.job_race_condition_reap(reqd.jid)
        pkdc('{}: is_processing and not is_running', reqd.jid)
        is_processing = False
    template = sirepo.template.import_module(req.type)
    if is_processing:
        if not reqd.cached_data:
            return _subprocess_error(
                error='input file not found, but job is running',
                input_file=reqd.input_file,
            )
    else:
        is_running = False
        if reqd.run_dir.exists():
            res = simulation_db.read_result(reqd.run_dir)
            if res.state == sirepo.job.ERROR:
                return _subprocess_error(
                    error='read_result error: ' + res.get('error', '<no error in read_result>'),
                    run_dir=reqd.run_dir,
                )
            if (
                in_run_simulation and res.state == sirepo.job.COMPLETED
                and hasattr(template, 'prepare_output_file')
            ):
                template.prepare_output_file(reqd.run_dir, req.req_data)
                res = simulation_db.read_result(reqd.run_dir)
    if reqd.is_parallel:
        new = template.background_percent_complete(
            reqd.model_name,
            reqd.run_dir,
            is_running,
        )
        new.setdefault('percentComplete', 0.0)
        new.setdefault('frameCount', 0)
        res.update(new)
    res['parametersChanged'] = reqd.parameters_changed
    if res['parametersChanged']:
        pkdlog(
            '{}: parametersChanged=True req_hash={} cached_hash={}',
            reqd.jid,
            reqd.req_hash,
            reqd.cached_hash,
        )
    if reqd.is_parallel and reqd.cached_data:
        s = reqd.cached_data.models.computeJobCacheKey
        t = s.get('computeJobSerial', 0)
        res.pksetdefault(
            computeJobHash=s.computeJobHash,
            computeJobSerial=t,
            elapsedTime=lambda: int(
                (res.get('lastUpdateTime') or _mtime_or_now(reqd.run_dir)) - t
                if t else 0,
            ),
        )
    if is_processing:
        res.nextRequestSeconds = reqd.sim_data.poll_seconds(reqd.cached_data)
        res.nextRequest = PKDict(
            report=reqd.model_name,
            simulationId=reqd.cached_data.simulationId,
            simulationType=reqd.cached_data.simulationType,
            **reqd.cached_data.models.computeJobCacheKey
        )
    pkdc(
        '{}: processing={} state={} cache_hit={} cached_hash={} data_hash={}',
        reqd.jid,
        is_processing,
        res['state'],
        reqd.cache_hit,
        reqd.cached_hash,
        reqd.req_hash,
    )
    return res


def _start_simulation(data):
    """Setup and start the simulation.

    Args:
        data (dict): app data
    Returns:
        object: runner instance
    """
    s = data.models.computeJobCacheKey
    s.pkupdate(
        computeJobSerial=int(time.time()),
    )
    runner.job_start(data)


def _subprocess_error(**kwargs):
    """Something unexpected went wrong.

    Args:
        kwargs (dict): concatenated and logged
    Returns:
        dict: error response
    """
    pkdlog(
        'simulation_run_status error: {}',
        ' '.join(['{}={}'.format(k, v) for k,v in kwargs.items()]),
        pkdebug_frame=inspect.currentframe().f_back,
    )
    return {
        'state': 'error',
        'error': 'server error (see logs)',
    }
