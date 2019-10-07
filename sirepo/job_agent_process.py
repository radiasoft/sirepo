# -*- coding: utf-8 -*-
u"""Run jobs using a local process

:copyright: Copyright (c) 2018-2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkcollections import PKDict
from pykern import pkcollections
from pykern.pkdebug import pkdp, pkdexc, pkdlog
from sirepo import mpi
from sirepo.template import template_common
import os
import re
import subprocess
import tornado.process
import tornado.locks
import tornado.ioloop


#: Need to remove $OMPI and $PMIX to prevent PMIX ERROR:
# See https://github.com/radiasoft/sirepo/issues/1323
# We also remove SIREPO_ and PYKERN vars, because we shouldn't
# need to pass any of that on, just like runner.docker, doesn't
_EXEC_ENV_REMOVE = re.compile('^(OMPI_|PMIX_|SIREPO_|PYKERN_)')


async def run_extract_job(run_dir, cmd):
    env = _subprocess_env()
    # we're in py3 mode, and regular subprocesses will inherit our
    # environment, so we have to manually switch back to py2 mode.
    env['PYENV_VERSION'] = 'py2'
    cmd = ['pyenv', 'exec'] + cmd
    p = tornado.process.Subprocess(
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
        r = PKDict(
            stdout=bytearray(),
            stderr=bytearray(),
        )
        i = tornado.ioloop.IOLoop.current()
        i.spawn_callback(collect, p.stdout, r.stdout)
        i.spawn_callback(collect, p.stderr, r.stderr)
        r.returncode = await p.wait_for_exit(raise_error=False)
    except Exception:
        pkdlog(pkdexc())
    finally:
        p.proc.kill()
    return r


class ComputeJob(PKDict):
    def __init__(self, run_dir, jhash, status, cmd):
        self.run_dir = run_dir
        self.jhash = jhash
        self.status = status
        self.cancel_requested = False
        self.returncode = None
        self._wait_for_terminate_timeout = None
        self._process_exited = tornado.locks.Event()
        env = _subprocess_env()
        run_log_path = run_dir.join(template_common.RUN_LOG)
#rn wrap this; including exit call back
        # we're in py3 mode, and regular subprocesses will inherit our
        # environment, so we have to manually switch back to py2 mode.
        env['PYENV_VERSION'] = 'py2'
        cmd = ['pyenv', 'exec'] + cmd
        with open(run_log_path, 'a+b') as run_log:
            self._sub_process = tornado.process.Subprocess(
                cmd,
                cwd=run_dir,
                start_new_session=True,
                stdin=subprocess.DEVNULL,
                stdout=run_log,
                stderr=run_log,
                env=env,
            )
            self._sub_process.set_exit_callback(self._on_exit)

    async def kill(self, grace_period):
        self._wait_for_terminate_timeout = tornado.ioloop.IOLoop.current().call_later(
            grace_period,
            lambda: self._sub_process.proc.kill(),
        )
        return await self.wait_for_exit()

    def _on_exit(self, returncode):
        if self._wait_for_terminate_timeout:
            tornado.ioloop.IOLoop.current().remove_timeout(
                self._wait_for_terminate_timeout
            )

        self.returncode = returncode
        self._process_exited.set()

    async def wait_for_exit(self):
        await self._process_exited.wait()
        return self.returncode

    def __repr__(self):
        return 'run_dir={}, jhash={}, status={}'.format(
            self.run_dir,
            self.jhash,
            self.status,
        )


def _subprocess_env():
    env = PKDict(os.environ)
    pkcollections.unchecked_del(
        env,
        *(k for k in env if _EXEC_ENV_REMOVE.search(k)),
    )
    env.SIREPO_MPI_CORES = str(mpi.cfg.cores)
    return env
