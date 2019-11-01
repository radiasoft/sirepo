# -*- coding: utf-8 -*-
u"""Entry points for runner (v1)

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkjson
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp, pkdpretty
from sirepo import api_perm
from sirepo import http_reply
from sirepo import http_request
from sirepo import runner
from sirepo import simulation_db
from sirepo.template import template_common
import datetime
import hashlib
import sirepo.template
import time

_FRAME_KEYS = (
    'version',
    'frameIndex',
    'modelName',
    'simulationId',
    'simulationType',
    'computeJobHash',
    'computeJobStart',
)

#: What is_running?
_RUN_STATES = ('pending', 'running')

@api_perm.require_user
def api_runCancel():
    data = http_request.parse_data_input()
    jid = simulation_db.job_id(data)
    # TODO(robnagler) need to have a way of listing jobs
    # Don't bother with cache_hit check. We don't have any way of canceling
    # if the parameters don't match so for now, always kill.
    #TODO(robnagler) mutex required
    if runner.job_is_processing(jid):
        run_dir = simulation_db.simulation_run_dir(data)
        # Write first, since results are write once, and we want to
        # indicate the cancel instead of the termination error that
        # will happen as a result of the kill.
        try:
            simulation_db.write_result({'state': 'canceled'}, run_dir=run_dir)
        except IOError:
            # run_dir may have been deleted
            pass
        runner.job_kill(jid)
        # TODO(robnagler) should really be inside the template (t.cancel_simulation()?)
        # the last frame file may not be finished, remove it
        t = sirepo.template.import_module(data)
        if hasattr(t, 'remove_last_frame'):
            t.remove_last_frame(run_dir)
    # Always true from the client's perspective
    return http_reply.gen_json({'state': 'canceled'})


@api_perm.require_user
def api_runSimulation():
    data = http_request.parse_data_input(validate=True)
    res = _simulation_run_status(data, quiet=True)
    if (
        (
            not res['state'] in _RUN_STATES
            and (res['state'] != 'completed' or data.get('forceRun', False))
        ) or res.get('parametersChanged', True)
    ):
        try:
            _start_simulation(data)
        except runner.Collision:
            pkdlog('{}: runner.Collision, ignoring start', simulation_db.job_id(data))
        res = _simulation_run_status(data)
    return http_reply.gen_json(res)


@api_perm.require_user
def api_runStatus():
    return http_reply.gen_json(_simulation_run_status(http_request.parse_data_input()))


@api_perm.require_user
def api_simulationFrame(frame_id):
#rn this needs work. I need to encapsulate this so it is shared with the
#   javascript expliclitly (even if the code is not shared) especially
#   the order of the params. This would then be used by the extract job
#   not here so this should be a new type of job: simulation_frame
    #TODO(robnagler) startTime is computeJobHash; need version on URL and/or param names in URL
    v = frame_id.split('*')
    a = PKDict(zip(_FRAME_KEYS, v[:len(_FRAME_KEYS)]))
    assert a.version == 'v1'
    a.animationArgs = v[len(_FRAME_KEYS):]
    t = sirepo.template.import_module(a.simulationType)
    a.report = sirepo.sim_data.get_class(a.simulationType).animation_name(a)
    d = simulation_db.simulation_run_dir(a)
    f = t.get_simulation_frame(
        d,
        a,
        simulation_db.read_json(d.join(template_common.INPUT_BASE_NAME)),
    )
    r = http_reply.gen_json(f)
    if 'error' not in f and t.WANT_BROWSER_FRAME_CACHE:
        n = datetime.datetime.utcnow()
        e = n + datetime.timedelta(365)
#rn why is this public? this is not public data.
        r.headers['Cache-Control'] = 'public, max-age=31536000'
        r.headers['Expires'] = e.strftime("%a, %d %b %Y %H:%M:%S GMT")
        r.headers['Last-Modified'] = n.strftime("%a, %d %b %Y %H:%M:%S GMT")
    else:
        http_reply.headers_for_no_cache(r)
    return r


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


def _simulation_run_status(data, quiet=False):
    """Look for simulation status and output

    Args:
        data (dict): request
        quiet (bool): don't write errors to log

    Returns:
        dict: status response
    """
    rep = simulation_db.report_info(data)
    is_processing = runner.job_is_processing(rep.job_id)
    is_running = rep.job_status in _RUN_STATES
    is_parallel = simulation_db.is_parallel(data)
    res = PKDict(state=rep.job_status)
    pkdc(
        '{}: is_processing={} is_running={} state={} cached_data={}',
        rep.job_id,
        is_processing,
        is_running,
        rep.job_status,
        bool(rep.cached_data),
    )
    if is_processing and not is_running:
        runner.job_race_condition_reap(rep.job_id)
        pkdc('{}: is_processing and not is_running', rep.job_id)
        is_processing = False
    template = sirepo.template.import_module(data)
    if is_processing:
        if not rep.cached_data:
            return _subprocess_error(
                error='input file not found, but job is running',
                input_file=rep.input_file,
            )
    else:
        is_running = False
        if rep.run_dir.exists():
            if hasattr(template, 'prepare_output_file') and 'models' in data:
                template.prepare_output_file(rep.run_dir, data)
            res2, err = simulation_db.read_result(rep.run_dir)
            if err:
                if is_parallel:
                    # allow parallel jobs to use template to parse errors below
                    res['state'] = 'error'
                else:
                    if hasattr(template, 'parse_error_log'):
                        res = template.parse_error_log(rep.run_dir)
                        if res:
                            return res
                    return _subprocess_error(read_result=err, run_dir=rep.run_dir)
            else:
                res = res2
    if simulation_db.is_parallel(data):
        new = template.background_percent_complete(
            rep.model_name,
            rep.run_dir,
            is_running,
        )
        new.setdefault('percentComplete', 0.0)
        new.setdefault('frameCount', 0)
        res.update(new)
    res['parametersChanged'] = rep.parameters_changed
    if res['parametersChanged']:
        pkdlog(
            '{}: parametersChanged=True req_hash={} cached_hash={}',
            rep.job_id,
            rep.req_hash,
            rep.cached_hash,
        )
    if is_parallel and rep.cached_data:
        s = rep.cached_data.models.computeJobStatus
        t = s.get('computeJobStart')
        res.pksetdefault(
            computeJobHash=s.computeJobHash,
            computeJobStart=t,
            elapsedTime=lambda: (
                res.get('lastUpdateTime') or _mtime_or_now(rep.run_dir)
            ) - t,
        )
    if is_processing:
        res.nextRequestSeconds = simulation_db.poll_seconds(rep.cached_data)
        res.nextRequest = PKDict(
            report=rep.model_name,
            simulationId=rep.cached_data.simulationId,
            simulationType=rep.cached_data.simulationType,
            **rep.cached_data.models.computeJobStatus
        )
    pkdc(
        '{}: processing={} state={} cache_hit={} cached_hash={} data_hash={}',
        rep.job_id,
        is_processing,
        res['state'],
        rep.cache_hit,
        rep.cached_hash,
        rep.req_hash,
    )
    return pkdp(res)


def _start_simulation(data):
    """Setup and start the simulation.

    Args:
        data (dict): app data
    Returns:
        object: runner instance
    """
    s = data.models.computeJobStatus
    s.pkupdate(
        computeJobStart=int(time.time()),
        state='pending',
    );
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
    )
    return {
        'state': 'error',
        'error': 'server error (see logs)',
    }
