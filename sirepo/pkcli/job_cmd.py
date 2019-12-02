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
from pykern.pkdebug import pkdp, pkdexc, pkdc, pkdlog
from sirepo import job
from sirepo import simulation_db
from sirepo.template import template_common
import functools
import os
import re
import requests
import sirepo.template
import subprocess
import sys
import time


def default_command(in_file):
    """Reads `in_file` passes to `msg.jobCmd`

    Must be called in run_dir

    Writes its output on stdout.

    Args:
        in_file (str): json parsed to msg
    Returns:
        str: json output of command, e.g. status msg
    """
    f = pkio.py_path(in_file)
    msg = pkjson.load_any(f)
#TODO(e-carlin): find common place to serialize/deserialize paths
    msg.runDir = pkio.py_path(msg.runDir)
    f.remove()
    return pkjson.dump_pretty(
        PKDict(
            globals()['_do_' + msg.jobCmd](
                msg,
                sirepo.template.import_module(msg.simulationType)
            )
        ).pksetdefault(state=job.COMPLETED),
        pretty=False,
    )


def _background_percent_complete(msg, template, is_running):
    r = template.background_percent_complete(
        msg.data.report,
        msg.runDir,
        is_running,
    )
#TODO(robnagler) this is incorrect, because we want to see file updates
#   not just our polling frequency
    r.pksetdefault(lastUpdateTime=lambda: _mtime_or_now(msg.runDir))
    r.pksetdefault(frameCount=0)
    r.pksetdefault(percentComplete=0.0)
    return r


def _do_cancel(msg, template):
    if hasattr(template, 'remove_last_frame'):
        template.remove_last_frame(msg.runDir)
    return PKDict()


def _do_compute(msg, template):
    msg.runDir = pkio.py_path(msg.runDir)
    msg.simulationStatus = PKDict(
        computeJobStart=int(time.time()),
        state=job.RUNNING,
    )
    try:
        with msg.runDir.join(template_common.RUN_LOG).open('w') as run_log:
            p = subprocess.Popen(
                _do_prepare_simulation(msg, template).cmd,
                stdout=run_log,
                stderr=run_log,
            )
        while True:
            for j in range(20):
                time.sleep(.1)
                r = p.poll()
                i = r is None
                if not i:
                    break
            if msg.isParallel:
                # TODO(e-carlin): This has a potential to fail. We likely
                # don't want the job to fail in this case
                _write_parallel_status(msg, template, i)
            if i:
                continue
            if r != 0:
                return PKDict(state=job.ERROR, error='non zero returncode={}'.format(r))
            else:
                return PKDict(state=job.COMPLETED)
    except Exception as e:
        return PKDict(state=job.ERROR, error=str(e), stack=pkdexc())
    # DOES NOT RETURN


def _do_get_simulation_frame(msg, template):
    return template_common.sim_frame_dispatch(
        msg.data.copy().pkupdate(run_dir=msg.runDir),
    )


def _do_get_data_file(msg, template):
    try:
        f, c, _ = template.get_data_file(
            msg.runDir,
            msg.analysisModel,
            msg.frame,
            options=PKDict(suffix=msg.suffix),
        )
        requests.put(msg.dataFileUri + f, data=c).raise_for_status()
        return PKDict()
    except Exception as e:
        return PKDict(error=e, stack=pkdexc())


def _do_prepare_simulation(msg, template):
    return PKDict(
        cmd=simulation_db.prepare_simulation(
            msg.data,
            run_dir=msg.runDir,
        )[0],
    )


def _do_sbatch_status(msg, template):
    p = 'PENDING'
    s = pkio.path_path(msg.stopSentinel)
    while True:
        if s.exists():
            if job.COMPLETED not in s.read():
                return
            _write_parallel_status(msg, template, False)
            pkio.unchecked_remove(s)
            return PKDict(state=job.COMPLETED)
        time.sleep(msg.nextRequestSeconds)
        _write_parallel_status(msg, template, True)
    # DOES NOT RETURN


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


def _write_parallel_status(msg, template, is_running):
    sys.stdout.write(
        pkjson.dump_pretty(
            PKDict(
                state=job.RUNNING,
                parallelStatus=_background_percent_complete(msg, template, is_running),
            ),
            pretty=False,
        ) + '\n',
    )
