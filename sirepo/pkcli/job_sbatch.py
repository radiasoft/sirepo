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
import sirepo.template
from sirepo import job



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
