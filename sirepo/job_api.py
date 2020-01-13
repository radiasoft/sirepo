u"""Entry points for job execution

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkinspect, pkjson
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp, pkdpretty
from sirepo import api_perm
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
import sirepo.util


cfg = None

#: uri to reach job_supervisor with
SUPERVISOR_URI = None

#: how many call frames to search backwards to find the api_.* caller
_MAX_FRAME_SEARCH_DEPTH = 6

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
            _request(
                computeJobHash='unused',
                dataFileKey=t.basename,
                frame=int(frame),
                req_data=req.req_data,
                suffix=s,
            )
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
            _request_uri=SUPERVISOR_URI + sirepo.job.SERVER_PING_URI,
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
def api_runCancel():
    try:
        return _request()
    except Exception as e:
        pkdlog('ignoring exception={} stack={}', e, pkdexc())
    # Always true from the client's perspective
    return sirepo.http_reply.gen_json({'state': 'canceled'})


@api_perm.require_user
def api_runSimulation():
    r = _request_content(PKDict(fixup_old_data=True))
    # TODO(e-carlin): This should really be done in job_supervisor._lib_dir_symlink()
    # but that is outside of the Flask context so it won't work
    r.simulation_lib_dir = sirepo.simulation_db.simulation_lib_dir(r.simulationType)
    return _request(_request_content=r)


@api_perm.require_user
def api_runStatus():
    return _request()


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
def api_sbatchLogin():
    r = _request_content(PKDict(computeJobHash='unused'))
    r.sbatchCredentials = r.pkdel('data')
    return _request(_request_content=r)


def init_apis(*args, **kwargs):
    global SUPERVISOR_URI
#TODO(robnagler) if we recover connections with agents and running jobs remove this
    pykern.pkio.unchecked_remove(sirepo.job.LIB_FILE_ROOT, sirepo.job.DATA_FILE_ROOT)
    pykern.pkio.mkdir_parent(sirepo.job.LIB_FILE_ROOT)
    pykern.pkio.mkdir_parent(sirepo.job.DATA_FILE_ROOT)

    cfg = pykern.pkconfig.init(
            supervisor_ip=(
                sirepo.job.DEFAULT_IP,
                str,
                'ip address to reach supervisor on'
            ),
            supervisor_port=(
                sirepo.job.DEFAULT_PORT,
                int,
                'port to reach supervisor on'
            ),
    )
    SUPERVISOR_URI = sirepo.job.supervisor_uri(
        cfg.supervisor_ip,
        cfg.supervisor_port
    )


def _request(**kwargs):
    def get_api_name():
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
    u = k.pkdel('_request_uri') or SUPERVISOR_URI + sirepo.job.SERVER_URI
    c = k.pkdel('_request_content') or _request_content(k)
    c.pkupdate(
        api=get_api_name(),
        serverSecret=sirepo.job.cfg.server_secret,
    )
    r = requests.post(
        u,
        data=pkjson.dump_bytes(c),
        headers=PKDict({'Content-type': 'application/json'}),
        verify=sirepo.job.cfg.verify_tls,
    )
    r.raise_for_status()
    return pkjson.load_any(r.content)


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
#TODO(robnagler) relative to srdb root
        simulationId=lambda: s.parse_sid(d),
        simulationType=lambda: d.simulationType,
    ).pksetdefault(
#TODO(robnagler) configured by job_supervisor
        mpiCores=lambda: sirepo.mpi.cfg.cores if b.isParallel else 1,
    ).pkupdate(
        reqId=sirepo.job.unique_key(),
        runDir=str(simulation_db.simulation_run_dir(d)),
        uid=sirepo.auth.logged_in_user(),
    ).pkupdate(
        computeJid=s.parse_jid(d, uid=b.uid),
        userDir=str(sirepo.simulation_db.user_dir_name(b.uid)),
    )
    return _run_mode(b)


def _run_mode(request_content):
    if 'models' not in request_content.data:
        return request_content
#TODO(robnagler) make sure this is set for animation sim frames
    m = request_content.data.models.get(request_content.computeModel)
    j = m and m.get('jobRunMode')
    if not j:
        request_content.jobRunMode = sirepo.job.PARALLEL if request_content.isParallel \
            else sirepo.job.SEQUENTIAL
        return request_content
    s = sirepo.sim_data.get_class(request_content.simulationType)
    for r in s.schema().common.enum.JobRunMode:
        if r[0] == j:
            return request_content.pkupdate(
                jobRunMode=j,
                sbatchCores=m.sbatchCores,
                sbatchHours=m.sbatchHours,
            )
    raise sirepo.util.Error(
        'jobRunMode={} computeModel={} computeJid={}'.format(
            j,
            request_content.computeModel,
            request_content.computeJid,
        )
    )
