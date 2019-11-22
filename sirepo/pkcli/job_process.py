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
import sirepo # TODO(e-carlin): fix
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
        PKDict(getattr(_SBatchProcess, 'do_' + msg.jobProcessCmd)(
            msg,
            sirepo.template.import_module(msg.simulationType)
        )).pkupdate(opDone=True),
        pretty=False,
    )


class _JobProcess(PKDict):

    @classmethod
    def _background_percent_complete(cls, msg, template):
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

    @classmethod
    def do_cancel(cls, msg, template):
        if hasattr(template, 'remove_last_frame'):
            template.remove_last_frame(msg.runDir)
        return PKDict()

    @classmethod
    def do_compute(cls, msg, template):
        msg.runDir = pkio.py_path(msg.runDir)
        with pkio.save_chdir('/'):
            pkio.unchecked_remove(msg.runDir)
            pkio.mkdir_parent(msg.runDir)
        msg.simulationStatus = PKDict(
            computeJobStart=int(time.time()),
            state=job.RUNNING,
        )
        try:
            cls._do_compute(msg, template)
        except Exception as e:
            return PKDict(state=job.ERROR, error=str(e), stack=pkdexc())
        return PKDict(state=job.COMPLETED)

    @classmethod
    def _do_compute(cls, msg, template):
        with open(
                str(msg.runDir.join(template_common.RUN_LOG)), 'w') as run_log:
            p = subprocess.Popen(
                simulation_db.prepare_simulation(
                    msg.data,
                    run_dir=msg.runDir
                )[0],
                stdout=run_log,
                stderr=run_log,
            )
        while True:
            r = p.poll()
            if msg.isParallel:
                msg.isRunning = r is None
                cls._write_parallel_status(msg, template)
            if r is None:
                time.sleep(2) # TODO(e-carlin): cfg
            else:
                assert r == 0, 'non zero returncode={}'.format(r)
                break

    @classmethod
    def _write_parallel_status(cls, msg, template):
        sys.stdout.write(
            pkjson.dump_pretty(
                PKDict(
                    state=job.RUNNING if msg.isRunning else job.COMPLETED,
                    parallelStatus=cls._background_percent_complete(msg, template),
                ),
                pretty=False,
            ) + '\n',
        )

    @classmethod
    def do_get_simulation_frame(cls, msg, template):
        return template_common.sim_frame_dispatch(
            msg.data.copy().pkupdate(run_dir=msg.runDir),
        )

    @classmethod
    def do_get_data_file(cls, msg, template):
        try:
            f, c, t = template.get_data_file(
                msg.runDir,
                msg.computeModel,
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

    @classmethod
    def do_sequential_result(cls, msg, template):
        r = simulation_db.read_result(msg.runDir)
        # Read this first: https://github.com/radiasoft/sirepo/issues/2007
        if (r.state != job.ERROR and hasattr(template, 'prepare_output_file')
            and 'models' in msg.data
        ):
            template.prepare_output_file(msg.runDir, msg.data)
            r = simulation_db.read_result(msg.runDir)
        return r


class _SBatchProcess(_JobProcess):

    @classmethod
    def _do_compute(cls, msg, template):
        o, e = subprocess.Popen(
            ('sbatch'),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        ).communicate(
            input=cls._get_sbatch_script(
                simulation_db.prepare_simulation(
                    msg.data,
                    run_dir=msg.runDir
                )[0],
                msg.runDir
            )
        )
        assert e == '', 'error={}'.format(e)
        r = re.search(r'\d+$', o)
        assert r is not None, 'output={} did not cotain job id'.format(o)
        job_id = r.group()
        while True:
            s = cls._get_sbatch_state(job_id)
            assert s in ('running', 'pending', 'completed'), \
                'invalid state={}'.format(s)
            if msg.isParallel:
                # TODO(e-carlin): We could read the squeue output to give the user
                # an idea of when a pending job will start
                # see --start flag on squeue
                # https://slurm.schedmd.com/squeue.html
                msg.isRunning = s == 'running'
                cls._write_parallel_status(msg, template)
            if s in ('running', 'pending'):
                time.sleep(2)
                continue
            break

    @classmethod
    def _get_sbatch_script(cls, cmd, run_dir):
        # TODO(e-carlin): configure the SBATCH* parameters
        return'''#!/bin/bash
#SBATCH --partition=compute
#SBATCH --ntasks=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=4
#SBATCH --mem-per-cpu=128M
#SBATCH -e {}
#SBATCH -o {}
docker run \
       --interactive \
       --init \
       --volume /home/vagrant/src:/home/vagrant/src:ro \
       --volume /home/vagrant/.pyenv:/home/vagrant/.pyenv:ro \
       --volume /home/vagrant/.local:/home/vagrant/.local:ro \
       --volume /home/vagrant/src/radiasoft/sirepo/run/user/0SICbY8N/:/home/vagrant/src/radiasoft/sirepo/run/user/0SICbY8N/ \
       --volume {}:{} \
       radiasoft/sirepo:dev \
       /bin/bash -l <<'EOF'
pyenv shell py2
cd {}
{}
EOF
    '''.format(
            template_common.RUN_LOG,
            template_common.RUN_LOG,
            run_dir,
            run_dir,
            run_dir,
            ' '.join(cmd),# TODO(e-carlin): quote?
        )

    @classmethod
    def _get_sbatch_state(cls, job_id):
        o = subprocess.check_output(
            ('scontrol', 'show', 'job', job_id)
        ).decode('utf-8')
        r = re.search(r'(?<=JobState=)(.*)(?= Reason)', o)
        assert r, 'output={}'.format(s)
        return r.group().lower()


def _mtime_or_now(path):
    """mtime for path if exists else time.time()

    Args:
        path (py.path):

    Returns:
        int: modification time
    """
    return int(path.mtime() if path.exists() else time.time())
