# -*- coding: utf-8 -*-
"""TODO(e-carlin): Doc

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkcollections
from pykern import pkconfig, pkio
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdlog, pkdexc, pkdc
import functools
import os
from sirepo import job_driver
import sirepo.job
import tornado.ioloop
import tornado.locks
import tornado.process


_KILL_TIMEOUT_SECS = 3

cfg = None

def init_class():
    # TODO(e-carlin): cfg should be at bottom like in other modules. Except that
    # class LocalDriver needs it which means it has to be declared before it
    global cfg

    cfg = pkconfig.init(
        parallel_slots=(1, int, 'max parallel slots'),
        sequential_slots=(1, int, 'max sequential slots'),
    )
    return LocalDriver.init_class()


class LocalDriver(job_driver.DriverBase):
    #TODO(robnagler) pkinspect this
    module_name = 'local'
#rn has to be here, because instances are class-basedx
    instances = pkcollections.Dict()

    def __init__(self, req, computeJob, *args, **kwargs):

        slot = await _Slot.get_instance(kind),
        super().__init__(*args, **kwargs)
        self._agent_dir = str(simulation_db.user_dir_name(self.uid).join('agent-local', self.agent_id))
        self._subprocess = None
        slot.in_use[slot.kind].append(self)
        self.instances[slot.kind][self.uid] = self
        self._start()

    @classmethod
    async def get_instance_for_op(cls, computeJob, op):
        k = 'parallel' if computeJob.is_parallel and op != job.OP_ANALYSIS \
            else 'sequential'
        self = cls.instances[k].get(req.uid)
        if self:
            await self.queue(req)
        else:
            self = await cls(req, computeJob)

    @classmethod
    def init_class(cls):
        for r in cls.RESOURCE_CLASSES:
            k = cls.get_kind(r)
            cls.instances[k] = PKDict()
            _Slot.init_kind(k, r)
        return cls

    def assign_job(self, job):
        self.jobs.append(job)

    def has_capacity(self, job):
        for j in self.jobs:
            if j.res.state == sirepo.job.Status.RUNNING.value:
                return False
        return True

    def __repr__(self):
        return '<agent_id={} kind={} jobs={}>'.format(
            self.agent_id,
            self.kind,
            self.jobs,
        )

    # TODO(e-carlin): If IoLoop.spawn_callback(self._stats) is deleted then
    # this can be deleted too.
    async def _stats(self):
        # TODO(e-carlin): This is used to get stats about drivers as the code
        # is running. Only useful when closely debugging code. Delete when stable.
        # tornado.ioloop.IOLoop.current().spawn_callback(
        #     self._stats
        # )
        import tornado.gen
        while True:
            pkdlog('{}', self)
            await tornado.gen.sleep(cfg.stats_secs)

    def kill(self):
        assert self._status
        pkdlog('{}', self)
        self._status = job_driver.Status.KILLING
        # TODO(e-carlin): What happens when an exception is thrown?
        if not self._subprocess:
            return
        self._kill_timeout = tornado.ioloop.IOLoop.current().call_later(
            _KILL_TIMEOUT_SECS,
            self._subprocess.proc.kill,
        )
        self._subprocess.proc.terminate()

    def _on_exit(self, returncode):
        pkdc(
            '{} returncode={} _agent_start_attemtps={}',
            self,
            returncode,
            self._start_attempts,
        )
        if self._kill_timeout:
            tornado.ioloop.IOLoop.current().remove_timeout(self._kill_timeout)
            self._kill_timeout = None
        del self.instances[self.agent_id]
        self.slot.in_use[self.kind].remove(self)
        self.slot.available[self.kind].put_nowait(_Slot(kind=self.kind))
        if self._status is not job_driver.Status.KILLING:
            self._on_agent_error_exit() # TODO(e-carlin): impl

    def _start(self):
        pkdlog('agent_id={}', self.agent_id)
        assert self._status != job_driver.Status.STARTING
        self._status = job_driver.Status.STARTING
        self._start_attempts += 1
        tornado.ioloop.IOLoop.current().spawn_callback(self._start_cb)

    async def _start_cb(self):
        pkdlog('agent_id={}', self.agent_id)
        env = dict(os.environ)
        env['PYENV_VERSION'] = 'py3'
        env['SIREPO_PKCLI_JOB_AGENT_AGENT_ID'] = self.agent_id
        env['SIREPO_PKCLI_JOB_AGENT_SUPERVISOR_URI'] = job_driver.cfg.supervisor_uri
        env['PYKERN_PKDEBUG_OUTPUT'] = '/dev/tty'
        env['PYKERN_PKDEBUG_REDIRECT_LOGGING'] = '1'
        env['PYKERN_PKDEBUG_CONTROL'] = '.*'
        pkio.mkdir_parent(self._agent_dir)
        self._subprocess = tornado.process.Subprocess(
            [
                'pyenv',
                'exec',
                'sirepo',
                'job_agent',
            ],
            cwd=str(self._agent_dir),
            env=env,
        )
        self._subprocess.set_exit_callback(self._on_exit)


class _Slot(PKDict):
    available = PKDict()
    in_use = PKDict()

    @classmethod
    def init_kind(cls, kind, resource_class):
        q = cls.available[kind] = tornado.queues.Queue()
        for _ in range(cfg[resource_class + '_slots']):
            q.put_nowait(_Slot(kind=kind, resource_class=resource_class))
        cls.in_use[kind] = []

    @classmethod
    async def garbage_collect_one(cls, kind):
        for d in cls.in_use[kind]:
            if not d.jobs:
                await d.kill()
                return

    @classmethod
    async def get_instance(cls, kind):
        try:
            return cls.available[kind].get_nowait()
        except tornado.queues.QueueEmpty:
            tornado.ioloop.IOLoop.current().spawn_callback(
                cls.garbage_collect_one,
                kind,
            )
            return await cls.available[kind].get()
