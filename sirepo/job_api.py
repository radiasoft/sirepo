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
            jid=simulation_db.job_id(data)
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
        jhash=template_common.report_parameters_hash(data),
        run_dir=simulation_db.simulation_run_dir(data),
        jid=simulation_db.job_id(data),
        parallel=simulation_db.is_parallel(data),
    )
    status = job.compute_job_status(b)
    if status not in job.ALREADY_GOOD_STATUS:
        data['simulationStatus'] = {
            'startTime': int(time.time()),
            'state': 'pending',
        }
        i = job.msg_id()
        d = run_dir.new(
            purebasename='-'.join((run_dir.purebasename, jhash, i)),
            ext=srdb.TMP_DIR_SUFFIX,
        )
        cmd, _ = simulation_db.prepare_simulation(data, tmp_dir=d)
        job.start_compute_job(
            body=PKDict(
                cmd=cmd,
                jhash=jhash,
                jid=jid,
                parallel=simulation_db.is_parallel(data),
                req_id=i,
                run_dir=run_dir,
                sim_id=data.simulationId,
                tmp_dir=d,
            ),
        )
#rn at this point, you'll
    res = _simulation_run_status_job_supervisor(data, quiet=True)
    return http_reply.gen_json(res)


@api_perm.require_user
def api_runStatus():
    return http_reply.gen_json(_simulation_run_status_job_supervisor(http_request.parse_data_input()))


@api_perm.require_user
def api_simulationFrame(frame_id):
#rn this needs work. I need to encapsulate this so it is shared with the
#   javascript expliclitly (even if the code is not shared) especially
#   the order of the params. This would then be used by the extract job
#   not here so this should be a new type of job: simulation_frame
    #TODO(robnagler) startTime is reportParametersHash; need version on URL and/or param names in URL
    keys = ['simulationType', 'simulationId', 'modelName', 'animationArgs', 'frameIndex', 'startTime']
#rn pkcollections.Dict
    data = PKDict(zip(keys, frame_id.split('*')))
    template = sirepo.template.import_module(data)
    data.report = template.get_animation_name(data)
    b = PKDict(
        jid=simulation_db.job_id(data),
        run_dir=simulation_db.simulation_run_dir(data),
        cmd='get_simulation_frame',
        arg=data,
    )
    b.jhash = template_common.report_parameters_hash(
        simulation_db.read_json(b.run_dir.join(template_common.INPUT_BASE_NAME)),
    )
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
            '{}: is_running={} state={}',
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
