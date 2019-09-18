# -*- coding: utf-8 -*-
u"""Entry points for runner (v1)

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkjson
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp, pkdpretty
from sirepo import api_perm
from sirepo import http_reply
from sirepo import http_request
from sirepo import runner
from sirepo import simulation_db
from sirepo.template import template_common
import datetime
import sirepo.template
import time


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
    #TODO(robnagler) startTime is reportParametersHash; need version on URL and/or param names in URL
    keys = ['simulationType', 'simulationId', 'modelName', 'animationArgs', 'frameIndex', 'startTime']
#rn pkcollections.Dict
    data = dict(zip(keys, frame_id.split('*')))
    template = sirepo.template.import_module(data)
    data['report'] = template.get_animation_name(data)
    run_dir = simulation_db.simulation_run_dir(data)
    model_data = simulation_db.read_json(run_dir.join(template_common.INPUT_BASE_NAME))
    frame = template.get_simulation_frame(run_dir, data, model_data)
    resp = http_reply.gen_json(frame)
    if 'error' not in frame and template.WANT_BROWSER_FRAME_CACHE:
        now = datetime.datetime.utcnow()
        expires = now + datetime.timedelta(365)
#rn why is this public? this is not public data.
        resp.headers['Cache-Control'] = 'public, max-age=31536000'
        resp.headers['Expires'] = expires.strftime("%a, %d %b %Y %H:%M:%S GMT")
        resp.headers['Last-Modified'] = now.strftime("%a, %d %b %Y %H:%M:%S GMT")
    else:
        http_reply.headers_for_no_cache(resp)
    return resp


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
    try:
        #TODO(robnagler): Lock
        rep = simulation_db.report_info(data)
        is_processing = runner.job_is_processing(rep.job_id)
        is_running = rep.job_status in _RUN_STATES
        res = {'state': rep.job_status}
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
                return http_reply.subprocess_error(
                    'input file not found, but job is running',
                    rep.input_file,
                )
        else:
            is_running = False
            if rep.run_dir.exists():
                if hasattr(template, 'prepare_output_file') and 'models' in data:
                    template.prepare_output_file(rep.run_dir, data)
                res2, err = simulation_db.read_result(rep.run_dir)
                if err:
                    if simulation_db.is_parallel(data):
                        # allow parallel jobs to use template to parse errors below
                        res['state'] = 'error'
                    else:
                        if hasattr(template, 'parse_error_log'):
                            res = template.parse_error_log(rep.run_dir)
                            if res:
                                return res
                        return http_reply.subprocess_error(err, 'error in read_result', rep.run_dir)
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
        #TODO(robnagler) verify serial number to see what's newer
        res.setdefault('startTime', _mtime_or_now(rep.input_file))
        res.setdefault('lastUpdateTime', _mtime_or_now(rep.run_dir))
        res.setdefault('elapsedTime', res['lastUpdateTime'] - res['startTime'])
        if is_processing:
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
            is_processing,
            res['state'],
            rep.cache_hit,
            rep.cached_hash,
            rep.req_hash,
        )
    except Exception:
        return http_reply.subprocess_error(pkdexc(), quiet=quiet)
    return res


def _start_simulation(data):
    """Setup and start the simulation.

    Args:
        data (dict): app data
    Returns:
        object: runner instance
    """
    data['simulationStatus'] = {
        'startTime': int(time.time()),
        'state': 'pending',
    }
    runner.job_start(data)
