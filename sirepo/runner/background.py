# -*- coding: utf-8 -*-
u"""Run jobs as subprocesses

:copyright: Copyright (c) 2016-2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp, pkdpretty
from sirepo import mpi
from sirepo import runner
from sirepo import simulation_db
from sirepo.template import template_common
import errno
import os
import re
import resource
import signal
import subprocess
import sys
import time

#: Need to remove $OMPI and $PMIX to prevent PMIX ERROR:
# See https://github.com/radiasoft/sirepo/issues/1323
# We also remove SIREPO_ and PYKERN vars, because we shouldn't
# need to pass any of that on, just like runner.docker, doesn't
_EXEC_ENV_REMOVE = re.compile('^(PMI_|OMPI_|PMIX_|SIREPO_|PYKERN_)')


class BackgroundJob(runner.JobBase):
    """Run as subprocess"""

    def __init__(self, *args, **kwargs):
        super(BackgroundJob, self).__init__(*args, **kwargs)
        self.__pid = None

    def _is_processing(self):
        try:
            os.kill(self.__pid, 0)
        except OSError:
            self.__pid = 0
            return False
        return True

    def _kill(self):
        if self.__pid == 0:
            return
        pid = self.__pid
        for sig in (signal.SIGTERM, signal.SIGKILL):
            try:
                pkdlog('{}: kill {} pid={}', self.jid, sig, self.__pid)
                os.kill(self.__pid, sig)
                for j in range(runner.KILL_TIMEOUT_SECS):
                    time.sleep(1)
                    pid, status = os.waitpid(self.__pid, os.WNOHANG)
                    if pid != 0:
                        break
                else:
                    continue
                if pid == self.__pid:
                    pkdlog('{}: waitpid: status={}', pid, status)
                    self.__pid = 0
                    break
                else:
                    pkdlog(
                        'pid={} status={}: unexpected waitpid result; job={} pid={}',
                        pid,
                        status,
                        self.jid,
                        self.__pid,
                    )
            except OSError as e:
                if not e.errno in (errno.ESRCH, errno.ECHILD):
                    raise
                # reaped by _sigchld_handler()
                return

    @classmethod
    def _sigchld_handler(cls, signum=None, frame=None):
        try:
#TODO(robnagler) not pretty; need a better solution
            with runner._job_map_lock:
                if not runner._job_map:
                    # Can't be our job so don't waitpid.
                    # Only important at startup, when other modules
                    # are doing popens, which does a waitpid.
                    # see radiasoft/sirepo#681
                    return
                pid, status = os.waitpid(-1, os.WNOHANG)
                if pid == 0:
                    # a process that was reaped before sigchld called
                    return
                for self in runner._job_map.values():
                    # state of '__pid' is unknown since outside self.lock
                    if isinstance(self, BackgroundJob) and self.__pid == pid:
                        pkdlog('{}: waitpid pid={} status={}', self.jid, pid, status)
                        break
                else:
                    pkdlog('pid={} status={}: unexpected waitpid', pid, status)
                    return
            with self.lock:
                self.__pid = 0
                self.kill()
        except OSError as e:
            if not e.errno in (errno,ESRCH, errno.ECHILD):
                pkdlog('waitpid: OSError: {} errno={}', e.strerror, e.errno)

    def _start(self):
        """Detach a process from the controlling terminal and run it in the
        background as a daemon.

        We don't use pksubprocess. This method is not called from the MainThread
        so can't set signals.
        """
        env = _safe_env()
        env['SIREPO_MPI_CORES'] = str(mpi.cfg.cores)
        try:
            pid = os.fork()
        except OSError as e:
            pkdlog('{}: fork OSError: {} errno={}', self.jid, e.strerror, e.errno)
            reraise
        if pid != 0:
            pkdlog('{}: started: pid={} cmd={}', self.jid, pid, self.cmd)
            self.__pid = pid
            return
        try:
            os.chdir(str(self.run_dir))
            #Don't os.setsid() so signals propagate properly
            maxfd = resource.getrlimit(resource.RLIMIT_NOFILE)[1]
            if (maxfd == resource.RLIM_INFINITY):
                maxfd = runner.MAX_OPEN_FILES
            for fd in range(0, maxfd):
                try:
                    os.close(fd)
                except OSError:
                    pass
            sys.stdin = open(template_common.RUN_LOG, 'a+')
            assert sys.stdin.fileno() == 0
            os.dup2(0, 1)
            sys.stdout = os.fdopen(1, 'a+')
            os.dup2(0, 2)
            sys.stderr = os.fdopen(2, 'a+')
            pkdlog('{}: child will exec: {}', self.jid, self.cmd)
            sys.stderr.flush()
            try:
                simulation_db.write_status('running', self.run_dir)
                os.execvpe(self.cmd[0], self.cmd, env=env)
            except BaseException as e:
                pkdlog(
                    '{}: execvp error: {} errno={}',
                    self.jid,
                    e.strerror if hasattr(e, 'strerror') else '',
                    e.errno if hasattr(e, 'errno') else '',
                )
            finally:
                sys.exit(1)
        except BaseException as e:
            # NOTE: there's no lock here so just append to the log. This
            # really shouldn't happen, but it might (out of memory) so just
            # log to the run log and hope somebody notices
            self._error_during_start(e, pkdexc())
            raise


def _safe_env():
    return dict(
        [(k, v) for k, v in os.environ.items() if not _EXEC_ENV_REMOVE.search(k)],
    )


def init_class(app, *args, **kwargs):
    assert not app.sirepo_uwsgi, \
        'uwsgi does not work if sirepo.runner.cfg.job_class=background'
    signal.signal(signal.SIGCHLD, BackgroundJob._sigchld_handler)
    return BackgroundJob
