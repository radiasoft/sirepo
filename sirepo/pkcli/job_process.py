# -*- coding: utf-8 -*-
u"""Operations run inside the report directory to extract data.

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkcollections
from pykern import pkio
from pykern import pkjson
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp
from sirepo import job
from sirepo import mpi
from sirepo import simulation_db
from sirepo.template import template_common
import functools
import os
import re
import sirepo
import sirepo.sim_data
import subprocess
import sys
import time


#: Need to remove $OMPI and $PMIX to prevent PMIX ERROR:
# See https://github.com/radiasoft/sirepo/issues/1323
# We also remove SIREPO_ and PYKERN vars, because we shouldn't
# need to pass any of that on, just like runner.docker, doesn't
_EXEC_ENV_REMOVE = re.compile('^(OMPI_|PMIX_|SIREPO_|PYKERN_)')


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
        globals()['_do_' + msg.jobProcessCmd](
            msg,
            sirepo.template.import_module(msg.simulationType),
        ),
        pretty=False,
    )


def _do_background_percent_complete(msg, template):
    r = template.background_percent_complete(
        msg.data.report,
        msg.runDir,
        msg.isRunning,
    )
    r.setdefault('percentComplete', 0.0)
    r.setdefault('frameCount', 0)
    return _fix_status(r)


def _do_cancel(msg, template):
    if hasattr(template, 'remove_last_frame'):
        template.remove_last_frame(msg.runDir)
    return PKDict()


def _do_compute(msg, template):
    msg.runDir = pkio.py_path(msg.runDir)
    with pkio.save_chdir('/'):
        pkio.unchecked_remove(msg.runDir)
        pkio.mkdir_parent(msg.runDir)
    msg.data['simulationStatus'] = {
        'startTime': int(time.time()),
        'state': job.RUNNING,
    }
    cmd, _ = simulation_db.prepare_simulation(msg.data, run_dir=msg.runDir)
    try:
        pksubprocess.check_call_with_signals(
            ['pyenv', 'exec'] + cmd,
            output=msg.runDir.join(template_common.RUN_LOG),
        )
    except Exception as e:
        return PKDict(state=job.ERROR, error=str(e))
    r = _do_background_percent_complete(msg, template) if msg.isParallel else PKDict()

    return r



def _do_get_simulation_frame(msg, template):
    return template.get_simulation_frame(
        msg.runDir,
        msg.data,
        simulation_db.read_json(msg.runDir.join(template_common.INPUT_BASE_NAME)),
    )


def _do_sequential_result(msg, template):
    r = simulation_db.read_result(msg.runDir)
    # Read this first: https://github.com/radiasoft/sirepo/issues/2007
    if (r.state != job.ERROR and hasattr(template, 'prepare_output_file')
       and 'models' in msg.data
    ):
        template.prepare_output_file(msg.runDir, msg.data)
        r = simulation_db.read_result(msg.runDir)
    return r


def _fix_status(r):
    r.startTime = _mtime_or_now(rep.input_file)
        res.setdefault('lastUpdateTime', _mtime_or_now(rep.run_dir))
        res.setdefault('elapsedTime', res['lastUpdateTime'] - res['startTime'])
