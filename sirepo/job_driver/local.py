# -*- coding: utf-8 -*-
"""Runs processes on the current host

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkconfig, pkio
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdlog
from sirepo import job
from sirepo import job_driver
import sirepo.mpi
import subprocess
import tornado.ioloop
import tornado.process
import tornado.queues


class LocalDriver(job_driver.DriverBase):
    cfg = None

    __instances = PKDict({k: [] for k in job.KINDS})

    __cpu_slot_q = PKDict()

    def __init__(self, op):
        super().__init__(op)
        self.update(
            _agent_exec_dir=pkio.py_path(op.msg.userDir).join(
                "agent-local",
                self._agent_id,
            ),
            _agent_exit=tornado.locks.Event(),
        )
        self.cpu_slot_q = self.__cpu_slot_q[op.kind]
        self.__instances[self.kind].append(self)

    @classmethod
    def get_instance(cls, op):
        # TODO(robnagler) need to introduce concept of parked drivers for reallocation.
        # a driver is freed as soon as it completes all its outstanding ops. For
        # _run(), this is an outstanding op, which holds the driver until the _run()
        # is complete. Same for analysis. Once all runs and analyses are compelte,
        # free the driver, but park it. Allocation then is trying to find a parked
        # driver then a free cpu slot. If there are no free slots, we garbage collect
        # parked drivers. We can park more drivers than are available for compute
        # so has to connect to the max slots. Parking is only needed for resources
        # we have to manage (local, docker). For NERSC, AWS, etc. parking is not
        # necessary. You would allocate as many parallel slots. We can park more
        # slots than are in_use, just can't use more slots than are actually allowed.

        # TODO(robnagler) drivers are not organized by uid, because there can be more
        # than one per user, rather, we can have a list here, not just self.
        # need to have an allocation per user, e.g. 2 sequential and one 1 parallel.
        # _Slot() may have to understand this, because related to parking. However,
        # we are parking a driver so maybe that's a (local) driver mechanism
        for d in cls.__instances[op.kind]:
            # SECURITY: must only return instances for authorized user
            if d.uid == op.msg.uid:
                return d
        return cls(op)

    @classmethod
    def init_class(cls, job_supervisor):
        cls.cfg = pkconfig.init(
            agent_starting_secs=(
                cls._AGENT_STARTING_SECS_DEFAULT,
                int,
                "how long to wait for agent start",
            ),
            slots=dict(
                parallel=(1, int, "max parallel slots"),
                sequential=(1, int, "max sequential slots"),
            ),
            supervisor_uri=job.DEFAULT_SUPERVISOR_URI_DECL,
        )
        cls.__cpu_slot_q.update(
            {k: job_supervisor.SlotQueue(cls.cfg.slots[k]) for k in job.KINDS}
        )
        return cls

    async def kill(self):
        if "subprocess" not in self:
            return
        try:
            pkdlog("{} pid={}", self, self.subprocess.proc.pid)
            self.subprocess.proc.terminate()
            self.kill_timeout = tornado.ioloop.IOLoop.current().call_later(
                job_driver.KILL_TIMEOUT_SECS,
                self.subprocess.proc.kill,
            )
            await self._agent_exit.wait()
            self._agent_exit.clear()
        except Exception as e:
            pkdlog("{} error={} stack={}", self, e, pkdexc())

    async def prepare_send(self, op):
        if op.op_name == job.OP_RUN:
            op.msg.mpiCores = sirepo.mpi.cfg().cores if op.msg.isParallel else 1
        return await super().prepare_send(op)

    def _agent_on_exit(self, returncode):
        self._agent_exit.set()
        self.pkdel("subprocess")
        k = self.pkdel("kill_timeout")
        if k:
            tornado.ioloop.IOLoop.current().remove_timeout(k)
        pkdlog("{} returncode={}", self, returncode)
        self._agent_exec_dir.remove(rec=True, ignore_errors=True)

    async def _do_agent_start(self, op):
        stdin = None
        try:
            cmd, stdin, env = self._agent_cmd_stdin_env(op, cwd=self._agent_exec_dir)
            pkdlog("{} agent_exec_dir={}", self, self._agent_exec_dir)
            # since this is local, we can make the directory; useful for debugging
            pkio.mkdir_parent(self._agent_exec_dir)
            self.subprocess = tornado.process.Subprocess(
                cmd,
                cwd=self._agent_exec_dir,
                env=env,
                stdin=stdin,
                stderr=subprocess.STDOUT,
            )
            self.subprocess.set_exit_callback(self._agent_on_exit)
        finally:
            if stdin:
                stdin.close()


CLASS = LocalDriver
