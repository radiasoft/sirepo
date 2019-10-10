# -*- coding: utf-8 -*-
u"""Entry points for job execution

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkinspect, pkjson
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
import requests
import sirepo.template
import time


_YEAR = datetime.timedelta(365)


@api_perm.require_user
def api_runCancel():
    return _request()


@api_perm.require_user
def api_runSimulation():
    return _request(data=http_request.parse_data_input(validate=True))


@api_perm.require_user
def api_runStatus():
    return _request(data=http_request.parse_data_input())


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
#TODO(robnagler) should this be v2 or 2 like in animationArgs
#   probably need consistency anyway for dealing with separators
        assert f.pop(0) == 'v2', \
            'invalid frame_id={}'.format(frame_id)
        keys.append('computeHash')
    p = PKDict(zip(keys, f))
    template = sirepo.template.import_module(p)
    p.report = template.get_animation_name(p)
    p.compute_hash = p.get('computeHash')
    frame = _request(data=p)
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


def _request(**kwargs):
    b = _request_body(kwargs)
    import inspect
    b.setdefault(
        api=inspect.stack()[1][3],
        req_id=job.unique_key(),
        uid=simulation_db.uid_from_jid(b.compute_jid),
    )
    r = requests.post(
        job.cfg.supervisor_uri,
        data=pkjson.dump_bytes(b),
        headers=PKDict({'Content-type': 'application/json'}),
    )
    r.raise_for_status()
    pkdp('@@@@@@@@@@@@@ content={}', r.content)
    c = pkjson.load_any(r.content)
    if 'error' in c or c.get('action') == 'error':
        pkdlog('reply={} request={}', c, b)
        # TODO(e-carlin): Something better
        raise RuntimeError('Error. Please try agin.')
    return c


def _request_body(kwargs):
    b = PKDict(kwargs)
    d = b.get('data') or http_request.parse_data_input()
    for k, v in (
        ('analysis_model', lambda: d.report),
        ('compute_hash', lambda: template_common.report_parameters_hash(d)),
        ('compute_model', lambda: simulation_db.compute_job_model(d)),
        ('resource_class', lambda: 'parallel' if simulation_db.is_parallel(d) else 'sequential'),
        ('sim_type', lambda: d.simulationType),
        # depends on some of the above
        ('compute_jid', lambda: simulation_db.job_id(d).replace(b.analysis_model, b.compute_model)),
        ('analysis_jid', lambda: b.compute_jid + simulation_db.JOB_ID_SEP + b.analysis_model),
#TODO(robnagler) remove this
        ('run_dir', lambda: str(simulation_db.simulation_run_dir(d))),
    ):
        b[k] = d[k] if k in d else v()
    return b
