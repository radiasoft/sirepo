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
import pykern.pkio
import re
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

#: how many call frames to search backwards to find the api_.* caller
_MAX_FRAME_SEARCH_DEPTH = 6


@api_perm.require_user
def api_downloadDataFile(simulation_type, simulation_id, model, frame, suffix=None):
#TODO(robnagler) validate suffix and frame
    sim = sirepo.http_request.parse_params(
        id=simulation_id,
        model=model,
        type=simulation_type,
    )
    with simulation_db.tmp_dir() as d:
        # TODO(e-carlin): computeJobHash
        try:
            f = _request(
                data=PKDict(
                    sim.req_data,
                    frame=int(frame),
                    report=sim.model,
                    computeJobHash='x',
                    suffix=suffix,
                ),
                tmpDir=d
            ).file
        except requests.exceptions.HTTPError:
#TODO(robnagler) HTTPError is too coarse a check
            raise sirepo.util.raise_not_found(
                'frame={} not found {id} {type}'.format(frame, **sim)
            )
        return sirepo.http_reply.gen_file_as_attachment(pykern.pkio.py_path(f))

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
    return template_common.sim_frame(
        frame_id,
# TODO(e-carlin): remove 'report'. See comment about optional fields in _request_data()
        lambda a: _request(data=PKDict(report='x', **a))
    )


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
        #TODO(robnagler) pass for NERSC
        agentDbRoot=lambda: srdb.root(),
        analysisModel=d.report,
        api=get_api_name(),
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
