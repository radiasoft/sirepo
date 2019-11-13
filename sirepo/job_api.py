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
from sirepo import simulation_db
from sirepo import srdb
from sirepo import srtime
from sirepo.template import template_common
import calendar
import datetime
import flask
import inspect
import mimetypes
import pykern.pkio
import requests
import sirepo.auth
import sirepo.http_reply
import sirepo.http_request
import sirepo.job
import sirepo.mpi
import sirepo.sim_data
import sirepo.template
import sirepo.util
import time
import werkzeug.utils


_YEAR = datetime.timedelta(365)


@api_perm.require_user
def api_downloadDataFile(simulation_type, simulation_id, model, frame, suffix=None):
#TODO(robnagler) validate suffix and frame
    sim = sirepo.http_request.parse_params(
        id=simulation_id,
        model=model,
        type=simulation_type,
    )
    with simulation_db.tmp_dir() as d:
        # TODO(e-carlin): compueJobHash
        try:
            f = _request(
                data=PKDict(
                    sim.req_data,
                    frame=frame,
                    computeJobHash='x',
                    suffix=suffix,
                ),
                tmpDir=d
            ).file
        except requests.exceptions.HTTPError as e:
            pkdlog('error={} stack={}', e, pkdexc())
            raise sirepo.util.Error(error='file not found')
        f = pykern.pkio.py_path(d.join(werkzeug.utils.secure_filename(f)))
        m, _ = mimetypes.guess_type(f.basename)
        if m is None:
            m = 'application/octet-stream'
        return sirepo.http_reply.gen_file_as_attachment(f.read(), m, f.basename)

@api_perm.require_user
def api_runCancel():
    return _request()


@api_perm.require_user
def api_runSimulation():
    return _request(fixup_old_data=1)


@api_perm.require_user
def api_runStatus():
    return _request()


@api_perm.require_user
def api_simulationFrame(frame_id):
    # fram_id is parsed by template_common
    return template_common.sim_frame(frame_id, lambda a: _request(data=a))


def init_apis(*args, **kwargs):
    pass


def _request(**kwargs):
    r = requests.post(
        sirepo.job.cfg.supervisor_uri + sirepo.job.SERVER_URI,
        data=pkjson.dump_bytes(_request_data(PKDict(kwargs))),
        headers=PKDict({'Content-type': 'application/json'}),
    )
    r.raise_for_status()
    return pkjson.load_any(r.content)


def _request_data(kwargs):
    d = kwargs.pkdel('data')
    if not d:
        d = sirepo.http_request.parse_post(
            fixup_old_data=kwargs.pkdel('fixup_old_data'),
            id=1,
            model=1,
        ).req_data
    s = sirepo.sim_data.get_class(d)
    b = PKDict(data=d, **kwargs)
# TODO(e-carlin): some of these fields are only used for some type of reqs
# Ex tmpDir is only used in api_downloadDataFile
    return b.pksetdefault(
        analysisModel=d.report,
        api=inspect.currentframe().f_back.f_back.f_code.co_name,
        computeJid=lambda: s.parse_jid(d),
        computeJobHash=lambda: d.get('computeJobHash') or s.compute_job_hash(d),
        computeModel=lambda: s.compute_model(d),
        isParallel=lambda: s.is_parallel(d),
        reqId=sirepo.job.unique_key(),
        runDir=lambda: str(simulation_db.simulation_run_dir(d)),
        simulationType=d.simulationType,
        uid=sirepo.auth.logged_in_user(),
    ).pksetdefault(
        libDir=lambda: str(sirepo.simulation_db.simulation_lib_dir(b.simulationType)),
        mpiCores=lambda: sirepo.mpi.cfg.cores if b.isParallel else 1,
        userDir=lambda: str(sirepo.simulation_db.user_dir_name(b.uid)),
    )
