# -*- coding: utf-8 -*-
u"""Run jobs using a local process

:copyright: Copyright (c) 2018-2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function

from pykern import pkcollections
from pykern.pkdebug import pkdp
from sirepo import mpi
from sirepo.template import template_common
import os
import re
import subprocess
import tornado.process

#: Need to remove $OMPI and $PMIX to prevent PMIX ERROR:
# See https://github.com/radiasoft/sirepo/issues/1323
# We also remove SIREPO_ and PYKERN vars, because we shouldn't
# need to pass any of that on, just like runner.docker, doesn't
_EXEC_ENV_REMOVE = re.compile('^(OMPI_|PMIX_|SIREPO_|PYKERN_)')

def _subprocess_env():
    env = dict(os.environ)
    for k in list(env):
        if _EXEC_ENV_REMOVE.search(k):
            del env[k]
    env['SIREPO_MPI_CORES'] = str(mpi.cfg.cores)
    return env


def start_compute_job(run_dir, cmd):
    env = _subprocess_env()
    run_log_path = run_dir.join(template_common.RUN_LOG)
    # we're in py3 mode, and regular subprocesses will inherit our
    # environment, so we have to manually switch back to py2 mode.
    env['PYENV_VERSION'] = 'py2'
    cmd = ['pyenv', 'exec'] + cmd

    with open(run_log_path, 'a+b') as run_log:
        sub_process = tornado.process.Subprocess(
            cmd,
            cwd=run_dir,
            start_new_session=True,
            stdin=subprocess.DEVNULL,
            stdout=run_log,
            stderr=run_log,
            env=env,
        )
    # We don't use the pid for anything, but by putting it in the backend_info
    # we make sure it's available on disk in case someone is trying to debug
    # stuff by hand later.
    return _LocalReportJob(sub_process, {'pid': sub_process.pid})


class _LocalReportJob:
    def __init__(self, sub_process, backend_info):
        self._sub_process = sub_process
        self.backend_info = backend_info

    async def wait_for_exit(self):
        return await self._sub_process.wait_for_exit()

async def run_extract_job(io_loop, run_dir, cmd, backend_info):
    env = _subprocess_env()
    # we're in py3 mode, and regular subprocesses will inherit our
    # environment, so we have to manually switch back to py2 mode.
    env['PYENV_VERSION'] = 'py2'
    cmd = ['pyenv', 'exec'] + cmd
    
    sub_process = tornado.process.Subprocess(
        cmd,
        cwd=run_dir,
        start_new_session=True,
        stdin=subprocess.DEVNULL,
        stdout=tornado.process.Subprocess.STREAM,
        stderr=tornado.process.Subprocess.STREAM,
        env=env,
    )
    try:
        async def collect(stream, out_array):
            out_array += await stream.read_until_close()

        stdout = bytearray()
        stderr = bytearray()
         
        io_loop.spawn_callback(collect, sub_process.stdout, stdout)
        io_loop.spawn_callback(collect, sub_process.stderr, stderr)
        return_code = await sub_process.wait_for_exit()
    finally:
        #TODO(e-carlin): Do kill and close
        # sub_process.kill()
        # await sub_process.aclose()
        pass
    
    return pkcollections.Dict(
        returncode=return_code,
        stdout=stdout,
        stderr=stderr,
    )
