# -*- coding: utf-8 -*-
u"""sirepo package

:copyright: Copyright (c) 2018-2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function

from pykern import pkcollections
from sirepo import mpi
from sirepo.template import template_common
import os
import re
import subprocess
import trio

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


async def start_report_job(run_dir, cmd):
    env = _subprocess_env()
    run_log_path = run_dir.join(template_common.RUN_LOG)
    # we're in py3 mode, and regular subprocesses will inherit our
    # environment, so we have to manually switch back to py2 mode.
    env['PYENV_VERSION'] = 'py2'
    cmd = ['pyenv', 'exec'] + cmd
    with open(run_log_path, 'a+b') as run_log:
        trio_process = trio.Process(
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
    return _LocalReportJob(trio_process, {'pid': trio_process.pid})


class _LocalReportJob:
    def __init__(self, trio_process, backend_info):
        self._trio_process = trio_process
        self.backend_info = backend_info

    async def kill(self, grace_period):
        # Everything here is a no-op if the process is already dead
        self._trio_process.terminate()
        with trio.move_on_after(grace_period):
            await self._trio_process.wait()
        self._trio_process.kill()
        await self._trio_process.wait()

    async def wait(self):
        await self._trio_process.wait()
        return self._trio_process.returncode


async def run_extract_job(run_dir, cmd, backend_info):
    env = _subprocess_env()
    # we're in py3 mode, and regular subprocesses will inherit our
    # environment, so we have to manually switch back to py2 mode.
    env['PYENV_VERSION'] = 'py2'
    cmd = ['pyenv', 'exec'] + cmd

    # When the next version of Trio is released, we'll be able to replace all
    # this with a call to trio.run_process(...)
    trio_process = trio.Process(
        cmd,
        cwd=run_dir,
        start_new_session=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )
    try:
        async def collect(stream, out_array):
            while True:
                data = await stream.receive_some(4096)
                if not data:
                    break
                out_array += data

        stdout = bytearray()
        stderr = bytearray()
        async with trio.open_nursery() as nursery:
            nursery.start_soon(collect, trio_process.stdout, stdout)
            nursery.start_soon(collect, trio_process.stderr, stderr)
            await trio_process.wait()
    finally:
        trio_process.kill()
        await trio_process.aclose()

    return pkcollections.Dict(
        returncode=trio_process.returncode,
        stdout=stdout,
        stderr=stderr,
    )

    return stdout.decode('utf-8')
