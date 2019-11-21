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
from sirepo import job, simulation_db
import time
import subprocess
import sirepo.template
import re



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
    def wait_for_job_completion(job_id):
        s = 'pending'
        while s in ('running', 'pending'):
            o = subprocess.check_output(
                ('scontrol', 'show', 'job', job_id)
            ).decode('utf-8')
            r = re.search(r'(?<=JobState=)(.*)(?= Reason)', o)
            assert r, 'output={}'.format(s)
            s = r.group().lower()
            time.sleep(2) # TODO(e-carlin): cfg
        assert s == 'completed', 'output={}'.format(o)

    msg.runDir = pkio.py_path(msg.runDir)
    with pkio.save_chdir('/'):
        pkio.unchecked_remove(msg.runDir)
        pkio.mkdir_parent(msg.runDir)
    msg.simulationStatus = PKDict(
        computeJobStart=int(time.time()),
        state=job.RUNNING,
    )
    try:
        a = _get_sbatch_script(
                simulation_db.prepare_simulation(
                    msg.data,
                    run_dir=msg.runDir
                )[0])

        with open('slurmscript', 'w') as x:
            x.write(a)
        o, e = subprocess.Popen(
            ('sbatch'),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        ).communicate(
            input=a
        )
        assert e == '', 'error={}'.format(e)
        r = re.search(r'\d+$', o)
        assert r is not None, 'output={} did not cotain job id'.format(o)
        wait_for_job_completion(r.group())
        # TODO(e-carlin): parallel status
    except Exception as e:
        pkdc(pkdexc())
        return PKDict(state=job.ERROR, error=str(e))
    return PKDict(state=job.COMPLETED)


def _get_sbatch_script(cmd):
# TODO(e-carlin): configure the SBATCH* parameters
        return'''#!/bin/bash
#SBATCH --partition=compute
#SBATCH --ntasks=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=4
#SBATCH --mem-per-cpu=128M
{}
'''.format(' '.join(cmd)) # TODO(e-carlin): quote?
