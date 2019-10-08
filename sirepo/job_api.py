# -*- coding: utf-8 -*-
u"""Entry points for job execution

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp, pkdpretty
from sirepo import api_perm
from sirepo import http_reply
from sirepo import http_request
from sirepo import job
from sirepo import simulation_db
from sirepo import srdb
from sirepo import srtime
from sirepo.template import template_common
import calendar
import datetime
import sirepo.template
import time


_YEAR = datetime.timedelta(365)

@api_perm.require_user
def api_runCancel():
    data = http_request.parse_data_input()
    job.cancel_report_job(
        PKDict(
            jid=simulation_db.job_id(data),
            jhash=template_common.report_parameters_hash(data),
            run_dir=simulation_db.simulation_run_dir(data),
        ),
    )
    # Always true from the client's perspective
    return http_reply.gen_json(PKDict(state='canceled'))

@api_perm.require_user
def api_runSimulation():
    data = http_request.parse_data_input(validate=True)
    b = PKDict(
#TODO(robnagler) remove run_dir
        analysis_jid=simulation_db.job_id(data),
        analysis_model=data.report,
        compute_hash=template_common.report_parameters_hash(data),
        compute_model=simulation_db.compute_job_model(data),
        parallel=simulation_db.is_parallel(data),
        run_dir=simulation_db.simulation_run_dir(data),
    )
    b.compute_jid = _compute_jid(b)
    status = job.compute_job_status(b)
#TODO(robnagler) move into supervisor & agent
    if status not in job.ALREADY_GOOD_STATUS:
        data['simulationStatus'] = {
            'startTime': int(time.time()),
            'state': 'pending',
        }
        b.req_id = job.unique_key()
        d = simulation_db.tmp_dir()
#TODO(robnagler) prepare_simulation runs only in the agent
        cmd, _ = simulation_db.prepare_simulation(data, tmp_dir=d)
        job.start_compute_job(
            body=b.update(
                cmd=cmd,
                sim_id=data.simulationId,
                input_dir=d,
            ),
        )
    res = _simulation_run_status_job_supervisor(data, quiet=True)
    return http_reply.gen_json(res)


@api_perm.require_user
def api_runStatus():
    return http_reply.gen_json(_simulation_run_status_job_supervisor(http_request.parse_data_input()))


@api_perm.require_user
def api_simulationFrame(frame_id):
#TODO(robnagler) https://github.com/radiasoft/sirepo/issues/1557

#TODO(robnagler) this needs work. I need to encapsulate this so it is shared with the
#   javascript expliclitly (even if the code is not shared) especially
#   the order of the params. This would then be used by the extract job
#   not here so this should be a new type of job: simulation_frame

    f = frame_id.split('*')
    keys = ['simulationType', 'simulationId', 'modelName', 'animationArgs', 'frameIndex', 'startTime']
    if len(f) > len(keys):
        assert f.pop(0) == 'v2', \
            'invalid frame_id={}'.format(frame_id)
        keys.append('computeHash')
    p = PKDict(zip(keys, f))
    template = sirepo.template.import_module(p)
    p.report = template.get_animation_name(p)
    b = PKDict(
        analysis_jid=simulation_db.job_id(p),
        analysis_model=p.report,
        arg=p,
        cmd='get_simulation_frame',
        compute_hash=p.get('computeHash'),
        compute_model=simulation_db.compute_job_model(p),
        run_dir=simulation_db.simulation_run_dir(p),
    )
    b.compute_jid = _compute_jid(b)
    frame = job.run_extract_job(b)
    resp = http_reply.gen_json(frame)
    if 'error' not in frame and template.WANT_BROWSER_FRAME_CACHE:
        n = srtime.utc_now()
#TODO(robnagler) test non-public
        resp.headers.update({
            'Cache-Control': 'public, max-age=31536000',
            'Expires': _rfc1123(n + _YEAR),
            'Last-Modified': _rfc1123(n),
        })
    else:
        http_reply.headers_for_no_cache(resp)
    return resp


def init_apis(*args, **kwargs):
    pass


def _compute_jid(body):
    """Replace data.report with run_dir.basename

    This is a hack to support the concept of compute_jid,
    distinct from analysis_jid.
    """
#TODO(robnagler) compute_model should be added to data at the same
#   time data.report (analysis_model) is set
    return body.analysis_jid.replace(body.analysis_model, body.compute_model)


def _rfc1123(dt):
    return wsgiref.handlers.format_date_time(srtime.to_timestamp(dt))


def _mtime_or_now(path):
    """mtime for path if exists else time.time()

    Args:
        path (py.path):

    Returns:
        int: modification time
    """
    return int(path.mtime() if path.exists() else time.time())


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
        status = job.compute_job_status(b)
        is_running = status is job.Status.RUNNING
        rep = simulation_db.report_info(data)
        res = PKDict(state=status.value)
        pkdc(
            'jid={} is_running={} state={}',
            rep.job_id,
            is_running,
            status,
        )
        if not is_running:
            if status is not job.Status.MISSING:
                res, err = job.run_extract_job(b.setdefault(cmd='result'))
                if err:
                    return http_reply.subprocess_error(err, 'error in read_result', b.run_dir)
        if b.parallel:
            new = job.run_extract_job(
                b.setdefault(
                    cmd='background_percent_complete',
                    arg=is_running,
                ),
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
