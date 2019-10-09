# -*- coding: utf-8 -*-
"""TODO(e-carlin): Doc

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkcollections
from pykern import pkconfig
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
    LocalDriver.resources = PKDict(
        parallel=_Resources(cfg.parallel_slots),
        sequential=_Resources(cfg.sequential_slots),
    )
    _Slot.init_class(LocalDriver)
    return LocalDriver


class _Slot(object):
    available = PKDict()
    in_use = PKDict()

    @classmethod
    def init_class(cls, driver_class):
        for r in 'sequential', 'parallel':
            k = driver_class.get_kind(r)
            q = cls.available[k] = tornado.queues.Queue()
            for n in cfg[r + '_slots']:
                q.put_nowait(_Slot(kind=k))
            cls.in_use[k] = []


    @classmethod
    async def garbage_collect_one(cls, kind):
        for d in cls.in_use[kind]:
            if not d.jobs:
                await d.terminate()
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

    def __init__(self, *args, **kwargs):
        super().__init__(slot, job, *args, **kwargs)
        self.slot = slot
        self.kind = slot.kind
        self.jobs = [job]
        self.uid = job.uid
        self._subprocess = None
        self._start_attempts = 0
        self._max_start_attempts = 2
        self.killing = False
        self._terminate_timeout = None
        self._agent_exited = tornado.locks.Event()
        slot.in_use[slot.kind].append(self)


        # TODO(e-carlin): This is used to get stats about drivers as the code
        # is running. Only useful when closely debugging code. Delete when stable.
        # tornado.ioloop.IOLoop.current().spawn_callback(
        #     self._stats
        # )

    @classmethod
    async def get_instance(cls, job):
        for i in cls.instances[job.driver_kind].get(job.uid, []):
            # operating drvier case
            if job.jid in i.jobs:
                return i
        for i in cls.instances[job.driver_kind].get(job.uid, []):
            # cache driver case
            if i.has_capacity(job):
                return i.assign_job(job)
        return cls(
            await _Slot.get_instance(job.driver_kind),
            job,
        )


    def has_capacity(self, job):
        return self.jobs < 1


    def __repr__(self):
        return 'agent_id={} status={} running_data_jobs={} requests={} resources={}'.format(
            self.agent_id,
            self._status,
            self.running_data_jobs,
            self.requests,
            self.resources,
        )


    def slots_available(self):
        s = self.resources[self.resource_class].slots
        return len(s.in_use) < s.total

    def terminate(self):
        self._kill()


    # TODO(e-carlin): If IoLoop.spawn_callback(self._stats) is deleted then
    # this can be deleted too.
    async def _stats(self):
        import tornado.gen
        while True:
            pkdlog('{}', self)
            await tornado.gen.sleep(cfg.stats_secs)

    def _kill(self):
        assert self._status
        pkdlog('{}', self)
        # TODO(e-carlin): More error handling. If terminate doesn't work
        # we need to go to kill
        # TODO(e-carlin): What happens when an exception is thrown?
        self._status = sirepo.driver.Status.KILLING
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
        self.slot.in_use[self.kind].remove(self)
        self.slot.available[self.kind].put_nowait(self)
        if self._status is not sirepo.driver.Status.KILLING:
            self._on_agent_error_exit()

    def _start(self):
        self._status = sirepo.driver.Status.STARTING
        self._start_attempts += 1
        tornado.ioloop.IOLoop.current().spawn_callback(self._start_cb)

    def _start_cb(self):
        pkdlog('agent_id={}', self.agent_id)
        # TODO(e-carlin): Make this more robust. Ex handle failures,
        # monitor the process, be able to kill it
        env = dict(os.environ)
#rn wrap this in job_subprocess()
        env['PYENV_VERSION'] = 'py3'
#        env['PYKERN_PKDEBUG_OUTPUT'] = '/dev/tty'
#        env['PYKERN_PKDEBUG_CONTROL'] = 'job|driver'
#        env['PYKERN_PKDEBUG_WANT_PID_TIME'] = '1'
        env['SIREPO_PKCLI_JOB_AGENT_AGENT_ID'] = self.agent_id
        env['SIREPO_PKCLI_JOB_AGENT_SUPERVISOR_URI'] = self.supervisor_uri
#rn cwd is where? Probably should be a tmp directory
        pkio.mkdir_parent(msg.agent_dir)
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
