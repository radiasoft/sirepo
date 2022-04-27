u"""Entry points for job execution

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkcompat, pkinspect, pkjson
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp, pkdpretty
from sirepo import api_perm
from sirepo import http_reply
from sirepo import simulation_db
from sirepo.template import template_common
import inspect
import pykern.pkconfig
import pykern.pkio
import re
import requests
import sirepo.auth
import sirepo.http_reply
import sirepo.http_request
import sirepo.job
import sirepo.mpi
import sirepo.sim_data
import sirepo.uri_router
import sirepo.util


#: how many call frames to search backwards to find the api_.* caller
_MAX_FRAME_SEARCH_DEPTH = 6


def adjust_supervisor_srtime(days):
    return _request(
        api_name='not used',
        _request_content=PKDict(days=days),
        _request_uri=_supervisor_uri(sirepo.job.SERVER_SRTIME_URI),
    )

@api_perm.require_user
def api_admJobs():
    sirepo.auth.check_user_has_role(
        sirepo.auth.logged_in_user(),
        sirepo.auth_role.ROLE_ADM,
    )
    return _request(
        _request_content=PKDict(**sirepo.http_request.parse_post()),
    )


@api_perm.require_user
def api_analysisJob():
    return _request()


@api_perm.require_user
def api_downloadDataFile(simulation_type, simulation_id, model, frame, suffix=None):
#TODO(robnagler) validate suffix and frame
    req = sirepo.http_request.parse_params(
        id=simulation_id,
        model=model,
        type=simulation_type,
        check_sim_exists=True,
    )
    s = suffix and sirepo.srschema.parse_name(suffix)
    t = None
    with simulation_db.tmp_dir() as d:
        # TODO(e-carlin): computeJobHash
        t = sirepo.job.DATA_FILE_ROOT.join(sirepo.job.unique_key())
        t.mksymlinkto(d, absolute=True)
        try:
            r = _request(
                computeJobHash='unused',
                dataFileKey=t.basename,
                frame=int(frame),
                isParallel=False,
                req_data=req.req_data,
                suffix=s,
            )
            assert not r.state == 'error', f'error state in request=={r}'
            f = d.listdir()
            if len(f) > 0:
                assert len(f) == 1, \
                    'too many files={}'.format(f)
                return sirepo.http_reply.gen_file_as_attachment(f[0])
        except requests.exceptions.HTTPError:
#TODO(robnagler) HTTPError is too coarse a check
            pass
        finally:
            if t:
                pykern.pkio.unchecked_remove(t)
        raise sirepo.util.raise_not_found(
            'frame={} not found {id} {type}'.format(frame, **req)
        )


@api_perm.allow_visitor
def api_jobSupervisorPing():
    import requests.exceptions

    e = None
    try:
        k = sirepo.job.unique_key()
        r = _request(
            _request_content=PKDict(ping=k),
            _request_uri=_supervisor_uri(sirepo.job.SERVER_PING_URI),
        )
        if r.get('state') != 'ok':
            return r
        try:
            x = r.pknested_get('ping')
            if x == k:
                return r
            e = 'expected={} but got ping={}'.format(k, x)
        except KeyError:
            e = 'incorrectly formatted reply'
            pkdlog(r)
    except requests.exceptions.ConnectionError:
        e = 'unable to connect to supervisor'
    except Exception as e:
        pkdlog(e)
        e = 'unexpected exception'
    return PKDict(state='error', error=e)


@api_perm.require_user
def api_ownJobs():
    return _request(
        _request_content=PKDict(
            uid=sirepo.auth.logged_in_user(),
            **sirepo.http_request.parse_post()
        ),
    )


@api_perm.require_user
def api_runCancel():
    try:
        return _request()
    except Exception as e:
        pkdlog('ignoring exception={} stack={}', e, pkdexc())
    # Always true from the client's perspective
    return sirepo.http_reply.gen_json({'state': 'canceled'})


@api_perm.require_user
def api_runMulti():
    def _api(api):
        # SECURITY: Make sure we have permission to call API
        a = sirepo.uri_router.check_api_call(api).__name__
        # SECURITY: Only allow these two API's for now. Certain API's
        # (ex api_admJobs) have more security checks in the method (ex
        # check_user_has_role) in the Flask server that could be
        # circumvented since we don't call the Falsk server method.
        assert a in ('api_runSimulation', 'api_runStatus')
        return a

    r = []
    for m in sirepo.http_request.parse_json():
        c = _request_content(PKDict(req_data=m))
        c.data.pkupdate(api=_api(c.data.api), awaitReply=m.awaitReply)
        r.append(c)
    return _request(
        _request_content=PKDict(data=r),
        _request_uri=_supervisor_uri(sirepo.job.SERVER_RUN_MULTI_URI),
    )


@api_perm.require_user
def api_runSimulation():
    r = _request_content(PKDict(fixup_old_data=True))
    if r.isParallel:
        r.isPremiumUser = sirepo.auth.is_premium_user()
    return _request(_request_content=r)


@api_perm.require_user
def api_runStatus():
    return _request()


@api_perm.require_user
def api_sbatchLogin():
    r = _request_content(
        PKDict(computeJobHash='unused', jobRunMode=sirepo.job.SBATCH),
    )
    r.sbatchCredentials = r.pkdel('data')
    return _request(_request_content=r)


@api_perm.require_user
def api_simulationFrame(frame_id):
    return template_common.sim_frame(
        frame_id,
        lambda a: _request(
            analysisModel=a.frameReport,
            # simulation frames are always sequential requests even though
            # the report name has 'animation' in it.
            isParallel=False,
            req_data=PKDict(**a),
        )
    )


@api_perm.require_user
def api_statefulCompute():
    return _request_compute()


@api_perm.require_user
def api_statelessCompute():
    return _request_compute()


@api_perm.require_user
def api_wakeAgent():
    t = sirepo.http_request.parse_post().req_data.simulationType
    s = pkjson.load_any(pkcompat.from_bytes(sirepo.uri_router.call_api(
        'listSimulations',
        data=PKDict(simulationType=t),
    ).data))
    if not s:
        return
    return _request(
        req_data=pkjson.load_any(pkcompat.from_bytes(sirepo.uri_router.call_api(
            'simulationData',
            kwargs=PKDict(simulation_type=t, simulation_id=s[0].simulationId),
        ).data)),
    )


def init_apis(*args, **kwargs):
#TODO(robnagler) if we recover connections with agents and running jobs remove this
    pykern.pkio.unchecked_remove(sirepo.job.LIB_FILE_ROOT, sirepo.job.DATA_FILE_ROOT)
    pykern.pkio.mkdir_parent(sirepo.job.LIB_FILE_ROOT)
    pykern.pkio.mkdir_parent(sirepo.job.DATA_FILE_ROOT)


def _request(**kwargs):
    def get_api_name():
        if 'api_name' in kwargs:
            return kwargs['api_name']
        f = inspect.currentframe()
        for _ in range(_MAX_FRAME_SEARCH_DEPTH):
            m = re.search(r'^api_.*$', f.f_code.co_name)
            if m:
                return m.group()
            f = f.f_back
        else:
            raise AssertionError(
                '{}: max frame search depth reached'.format(f.f_code)
            )
    k = PKDict(kwargs)
    u = k.pkdel('_request_uri') or _supervisor_uri(sirepo.job.SERVER_URI)
    c = k.pkdel('_request_content') if '_request_content' in k else _request_content(k)
    c.pkupdate(
        api=get_api_name(),
        serverSecret=sirepo.job.cfg.server_secret,
    )
    pkdlog('api={} runDir={}', c.api, c.get('runDir'))
    r = requests.post(
        u,
        data=pkjson.dump_bytes(c),
        headers=PKDict({'Content-type': 'application/json'}),
        verify=sirepo.job.cfg.verify_tls,
    )
    r.raise_for_status()
    return pkjson.load_any(r.content)


def _request_compute():
    return _request(
        jobRunMode=sirepo.job.SEQUENTIAL,
        req_data=PKDict(
            **sirepo.http_request.parse_post().req_data,
        ).pkupdate(
            computeJobHash='unused',
            report='statefulOrStatelessCompute',
        ),
        runDir=None,
    )


def _request_content(kwargs):
    d = kwargs.pkdel('req_data')
    if not d:
#TODO(robnagler) need to use parsed values, ok for now, becasue none of
# of the used values are modified by parse_post. If we have files (e.g. file_type, filename),
# we need to use those values from parse_post
        d = sirepo.http_request.parse_post(
            fixup_old_data=kwargs.pkdel('fixup_old_data', False),
            id=True,
            model=True,
            check_sim_exists=True,
        ).req_data
    s = sirepo.sim_data.get_class(d)
##TODO(robnagler) this should be req_data
    b = PKDict(data=d, **kwargs)
# TODO(e-carlin): some of these fields are only used for some type of reqs
    b.pksetdefault(
        analysisModel=lambda: s.parse_model(d),
        computeJobHash=lambda: d.get('computeJobHash') or s.compute_job_hash(d),
        computeJobSerial=lambda: d.get('computeJobSerial', 0),
        computeModel=lambda: s.compute_model(d),
        isParallel=lambda: s.is_parallel(d),
        runDir=lambda: str(simulation_db.simulation_run_dir(d)),
#TODO(robnagler) relative to srdb root
        simulationId=lambda: s.parse_sid(d),
        simulationType=lambda: d.simulationType,
    ).pkupdate(
        reqId=sirepo.job.unique_key(),
        uid=sirepo.auth.logged_in_user(),
    ).pkupdate(
        computeJid=s.parse_jid(d, uid=b.uid),
        userDir=str(sirepo.simulation_db.user_path(b.uid)),
    )
    return _run_mode(b)


def _run_mode(request_content):
    if 'models' not in request_content.data or 'jobRunMode' in request_content:
        return request_content
#TODO(robnagler) make sure this is set for animation sim frames
    m = request_content.data.models.get(request_content.computeModel)
    j = m and m.get('jobRunMode')
    if not j:
        request_content.jobRunMode = sirepo.job.PARALLEL if request_content.isParallel \
            else sirepo.job.SEQUENTIAL
        return request_content
    if j not in simulation_db.JOB_RUN_MODE_MAP:
        raise sirepo.util.Error(
            'invalid jobRunMode',
            'invalid jobRunMode={} computeModel={} computeJid={}',
            j,
            request_content.computeModel,
            request_content.computeJid,
        )
    request_content.jobRunMode = j
    return _validate_and_add_sbatch_fields(request_content, m)


def _supervisor_uri(path):
    return cfg.supervisor_uri + path


def _validate_and_add_sbatch_fields(request_content, compute_model):
    m = compute_model
    c = request_content
    d = simulation_db.cfg.get('sbatch_display')
    if d and 'nersc' in d.lower():
        assert m.sbatchQueue in sirepo.job.NERSC_QUEUES, \
            f'sbatchQueue={m.sbatchQueue} not in NERSC_QUEUES={sirepo.job.NERSC_QUEUES}'
        c.sbatchQueue = m.sbatchQueue
        c.sbatchProject = m.sbatchProject
    for f in 'sbatchCores', 'sbatchHours':
        assert m[f] > 0, f'{f}={m[f]} must be greater than 0'
        c[f] = m[f]
    return request_content

cfg = pykern.pkconfig.init(
    supervisor_uri=sirepo.job.DEFAULT_SUPERVISOR_URI_DECL,
)
