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
import sirepo.driver
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
    _Slot.init_class(LocalDriver)
    LocalDriver.init_class()
    return LocalDriver


class _Slot(PKDict):
    available = PKDict()
    in_use = PKDict()

    @classmethod
    def init_class(cls, driver_class):
        for r in 'sequential', 'parallel':
            k = driver_class.get_kind(r)
            q = cls.available[k] = tornado.queues.Queue()
            for _ in range(cfg[r + '_slots']):
                q.put_nowait(_Slot(kind=k))
            cls.in_use[k] = []

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


class LocalDriver(sirepo.driver.DriverBase):
    #TODO(robnagler) pkinspect this
    module_name = 'local'

    def __init__(self, slot, job, *args, **kwargs):
        super().__init__(slot, job, *args, **kwargs)
        self._subprocess = None
        slot.in_use[slot.kind].append(self)
        self._start()

    @classmethod
    async def get_instance_for_job(cls, job):
        d = cls.instances[job.req.driver_kind].get(job.req.uid)
        if d:
            # operating drvier case
            for j in d.jobs:
                if job.jid == j.jid:
                    return d
            # cache driver case
            if d.has_capacity(job):
                return d.assign_job(job)
        return cls(
            await _Slot.get_instance(job.req.driver_kind),
            job,
        )

    @classmethod
    def init_class(cls):
        for r in 'sequential', 'parallel':
            cls.instances[cls.get_kind(r)] = PKDict()

    def assign_job(self, job):
        self.jobs.append(job)

    def has_capacity(self, job):
        return len(self.jobs) < 1

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
        self._status = sirepo.driver.Status.KILLING
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
        if self._status is not sirepo.driver.Status.KILLING:
            self._on_agent_error_exit() # TODO(e-carlin): impl

    def _start(self):
        pkdlog('agent_id={}', self.agent_id)
        assert self._status != sirepo.driver.Status.STARTING
        self._status = sirepo.driver.Status.STARTING
        self._start_attempts += 1
        tornado.ioloop.IOLoop.current().spawn_callback(self._start_cb)

    async def _start_cb(self):
        pkdlog('agent_id={}', self.agent_id)
        env = dict(os.environ)
        env['PYENV_VERSION'] = 'py3'
        env['SIREPO_PKCLI_JOB_AGENT_AGENT_ID'] = self.agent_id
        env['SIREPO_PKCLI_JOB_AGENT_SUPERVISOR_URI'] = sirepo.driver.cfg.supervisor_uri
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
