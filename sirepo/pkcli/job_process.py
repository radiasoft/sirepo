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
    """Reads `in_file` passes to `msg.job_process_cmd`

    Must be called in run_dir

    Writes its output on stdout.

    Args:
        in_file (str): json parsed to msg
    Returns:
        str: json output of command, e.g. status msg
    """
    f = pkio.py_path(in_file)
    msg = pkjson.load_any(f)
    msg.run_dir = pkio.py_path(msg.run_dir) # TODO(e-carlin): find common place to serialize/deserialize paths
    f.remove()
    return pkjson.dump_pretty(
        globals()['_do_' + msg.job_process_cmd](
            msg,
            sirepo.template.import_module(msg.sim_type),
        ),
        pretty=False,
    )


def _do_background_percent_complete(msg, template):
    r = template.background_percent_complete(
        msg.data.report,
        msg.run_dir,
        msg.is_running,
    )
    r.setdefault('percentComplete', 0.0)
    r.setdefault('frameCount', 0)
    return r


def _do_compute(msg, template):
    msg.run_dir = pkio.py_path(msg.run_dir)
    with pkio.save_chdir('/'):
        pkio.unchecked_remove(msg.run_dir)
        pkio.mkdir_parent(msg.run_dir)
    msg.data['simulationStatus'] = {
        'startTime': int(time.time()),
        'state': job.Status.PENDING.value, # TODO(e-carlin): Is this necessary?
    }
    cmd, _ = simulation_db.prepare_simulation(msg.data, run_dir=msg.run_dir)
    run_log_path = msg.run_dir.join(template_common.RUN_LOG)
    cmd = ['pyenv', 'exec'] + cmd
    with open(str(run_log_path), 'a+b') as run_log, open(os.devnull, 'w') as FNULL:
        p = None
        try:
            p = subprocess.Popen(
                cmd,
                cwd=str(msg.run_dir),
                stdin=FNULL,
                stdout=run_log,
                stderr=run_log,
                env=_subprocess_env(),
            )
            p.wait()
            p = None
        finally:
            if p:
                # TODO(e-carlin): terminate first?
                p.kill()
    return _do_compute_status(msg, template)
    # TODO(e-carlin): implement
    # if hasattr(template, 'remove_last_frame'):
    #     template.remove_last_frame(msg.run_dir)


def _do_compute_status(msg, template):
    """Legacy code path. Read status from simulation_db.

    In the legacy code path compute status was kept in a 'status' file in the db.
    This reads from that file. In the supervisor code path status is stored in
    the supervisor or in the job_agent._STATUS_FILE
    """
    d = simulation_db.read_json(simulation_db.json_filename(
        template_common.INPUT_BASE_NAME,
        msg.run_dir
    ))
    return PKDict(
        computeJobHash=sirepo.sim_data.get_class(d).compute_job_hash(d),
        lastUpdateTime=_mtime_or_now(msg.run_dir),
        # TODO(e-carlin): add startTime
        state=simulation_db.read_status(msg.run_dir),
    )


def _do_get_simulation_frame(msg, template):
    return template.get_simulation_frame(
        msg.run_dir,
        msg.data,
        simulation_db.read_json(msg.run_dir.join(template_common.INPUT_BASE_NAME)),
    )


def _do_result(msg, template):
    if hasattr(template, 'prepare_output_file') and 'models' in msg.data:
        template.prepare_output_file(msg.run_dir, msg.data)
    r, e = simulation_db.read_result(msg.run_dir)
    if not e:
        return PKDict(result=r)
    return PKDict(error=e)


def _subprocess_env():
    env = PKDict(os.environ)
    # pkcollections.unchecked_del(
    #     env,
    #     *(k for k in env if _EXEC_ENV_REMOVE.search(k))
    # )
    # env.SIREPO_MPI_CORES = str(mpi.cfg.cores)
    return env


def _mtime_or_now(path):
    """mtime for path if exists else time.time()

    Args:
        path (py.path):

    Returns:
        int: modification time
    """
    return int(path.mtime() if path.exists() else time.time())