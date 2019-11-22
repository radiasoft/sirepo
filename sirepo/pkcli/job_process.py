# -*- coding: utf-8 -*-
u"""Operations run inside the report directory to extract data.

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkcollections
from pykern import pkio
from pykern import pkjson
from pykern import pksubprocess
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdexc, pkdc
from sirepo import job
from sirepo import mpi
from sirepo import simulation_db
from sirepo.template import template_common
import functools
import os
import re
import requests
import sirepo
import subprocess
import sys
import time


def default_command(in_file):
    """Reads `in_file` passes to `msg.jobProcessCmd`

    Must be called in run_dir

    Writes its output on stdout.

    Args:
        in_file (str): json parsed to msg
    Returns:
        str: json output of command, e.g. status msg
    """
    f = pkio.py_path(in_file)
    msg = pkjson.load_any(f)
    msg.runDir = pkio.py_path(msg.runDir) # TODO(e-carlin): find common place to serialize/deserialize paths
    f.remove()
    return pkjson.dump_pretty(
        PKDict(globals()['_do_' + msg.jobProcessCmd](
            msg,
            sirepo.template.import_module(msg.simulationType),
        )).pkupdate(opDone=True),
        pretty=False,
    )


def _background_percent_complete(msg, template):
    r = template.background_percent_complete(
        msg.data.report,
        msg.runDir,
        msg.isRunning,
    )
    r.setdefault('computeJobStart', msg.simulationStatus.computeJobStart)
    r.setdefault('lastUpdateTime', _mtime_or_now(msg.runDir))
    r.setdefault('elapsedTime', r.lastUpdateTime - r.computeJobStart)
    r.setdefault('frameCount', 0)
    r.setdefault('percentComplete', 0.0)
    return r


def _do_cancel(msg, template):
    if hasattr(template, 'remove_last_frame'):
        template.remove_last_frame(msg.runDir)
    return PKDict()


def _do_compute(msg, template):
    msg.runDir = pkio.py_path(msg.runDir)
    with pkio.save_chdir('/'):
        pkio.unchecked_remove(msg.runDir)
        pkio.mkdir_parent(msg.runDir)
    msg.simulationStatus = PKDict(
        computeJobStart=int(time.time()),
        state=job.RUNNING,
    )
    cmd, _ = simulation_db.prepare_simulation(msg.data, run_dir=msg.runDir)
    try:
        with open(str(msg.runDir.join(template_common.RUN_LOG)), 'w') as run_log:
            p = subprocess.Popen(
                cmd,
                stdout=run_log,
                stderr=run_log,
            )
        while True:
            r = p.poll()
            if msg.isParallel:
                msg.isRunning = r is None
                sys.stdout.write(
                    pkjson.dump_pretty(
                        PKDict(
                            state=job.RUNNING if msg.isRunning else job.COMPLETED,
                            parallelStatus=_background_percent_complete(msg, template),
                        ),
                        pretty=False,
                    ) + '\n',
                )
            if r is None:
                time.sleep(2) # TODO(e-carlin): cfg
            else:
                assert r == 0, 'non zero returncode={}'.format(r)
                break
    except Exception as e:
        pkdc(pkdexc())
        return PKDict(state=job.ERROR, error=str(e))
    return PKDict(state=job.COMPLETED)


def _do_get_simulation_frame(msg, template):
    return template_common.sim_frame_dispatch(
        msg.data.copy().pkupdate(run_dir=msg.runDir),
    )


def _do_get_data_file(msg, template):
    try:
        f, c, t = template.get_data_file(
            msg.runDir,
            msg.analysisModel,
            int(msg.data.frame),
            options=PKDict(suffix=msg.data.suffix),
        )
        requests.put(
            # TODO(e-carlin): cfg
            msg.dataFileUri,
            files=[
                (msg.tmpDir, (f, c, t)),
            ],
        ).raise_for_status()
        return PKDict()
    except Exception as e:
        return PKDict(error=e, stack=pkdexc())


def _do_sequential_result(msg, template):
    r = simulation_db.read_result(msg.runDir)
    # Read this first: https://github.com/radiasoft/sirepo/issues/2007
    if (r.state != job.ERROR and hasattr(template, 'prepare_output_file')
       and 'models' in msg.data
    ):
        template.prepare_output_file(msg.runDir, msg.data)
        r = simulation_db.read_result(msg.runDir)
    return r


def _mtime_or_now(path):
    """mtime for path if exists else time.time()

    Args:
        path (py.path):

    Returns:
        int: modification time
    """
    return int(path.mtime() if path.exists() else time.time())
