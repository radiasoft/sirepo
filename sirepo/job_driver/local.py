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
from sirepo import job
from sirepo import job_driver
import os
import tornado.ioloop
import tornado.queues
import tornado.process


_KILL_TIMEOUT_SECS = 3

cfg = None


class LocalDriver(job_driver.DriverBase):

    module_name = 'local'

    users = pkcollections.Dict()

    def __init__(self, req, slot):
        super().__init__(req)
        self.update(
            agentDir=pkio.py_path(req.content.userDir).join('agent-local', self.agentId),
            kind=slot.kind,
            slot=slot,
        )
        self.users[self.kind][self.uid] = self
        tornado.ioloop.IOLoop.current().spawn_callback(self._agent_start)

    @classmethod
    async def allocate(cls, req):
#TODO(robnagler) need to introduce concept of parked drivers for reallocation.
# a driver is freed as soon as it completes all its outstanding ops. For
# _run(), this is an outstanding op, which holds the driver until the _run()
# is complete. Same for analysis. Once all runs and analyses are compelte,
# free the driver, but park it. Allocation then is trying to find a parked
# driver then a free slot. If there are no free slots, we garbage collect
# parked drivers. We can park more drivers than are available for compute
# so has to connect to the max slots. Parking is only needed for resources
# we have to manage (local, docker). For NERSC, AWS, etc. parking is not
# necessary. You would allocate as many parallel slots. We can park more
# slots than are in_use, just can't use more slots than are actually allowed.

#TODO(robnagler) drivers are not organized by uid, because there can be more
# than one per user, rather, we can have a list here, not just self.
# need to have an allocation per user, e.g. 2 sequential and one 1 parallel.
# _Slot() may have to understand this, because related to parking. However,
# we are parking a driver so maybe that's a (local) driver mechanism
        return cls.users[req.kind].get(req.content.uid) \
            or cls(req, await _Slot.allocate(req.kind))

    def _free(self):
        k = self.pkdel('kill_timeout')
        if k:
            tornado.ioloop.IOLoop.current().remove_timeout(k)
        self.pkdel('slot').free(self)
        del self.users[self.kind][self.uid]
        super()._free()

    @classmethod
    def init_class(cls):
        for k in job.KINDS:
            cls.users[k] = PKDict()
            _Slot.init_kind(k)
        return cls

    def kill(self):
        if 'subprocess' not in self:
            return
        self.subprocess.proc.terminate()
        self.kill_timeout = tornado.ioloop.IOLoop.current().call_later(
            _KILL_TIMEOUT_SECS,
            self.subprocess.proc.kill,
        )

    @classmethod
    async def send(cls, req, kwargs):
        return await (await cls.allocate(req))._send(req, kwargs)

    def terminate(self):
        if 'subprocess' in self:
            self.subprocess.proc.kill()

    def _agent_on_exit(self, returncode):
        pkcollections.unchecked_del(self, 'subprocess')
        self._free()

    async def _agent_start(self):
        pkio.mkdir_parent(self.agentDir)
#TODO(robnagler) SECURITY strip environment
        env = PKDict(os.environ).pkupdate(
            PYENV_VERSION='py3',
#TODO(robnagler) cascade from py test, not explicitly
            PYKERN_PKDEBUG_CONTROL='.',
            PYKERN_PKDEBUG_OUTPUT='/dev/tty',
            PYKERN_PKDEBUG_REDIRECT_LOGGING='1',
            PYKERN_PKDEBUG_WANT_PID_TIME='1',
            SIREPO_PKCLI_JOB_AGENT_AGENT_ID=self.agentId,
            SIREPO_PKCLI_JOB_AGENT_SUPERVISOR_URI=self.supervisor_uri,
        )
        self.subprocess = tornado.process.Subprocess(
            ['pyenv', 'exec', 'sirepo', 'job_agent'],
            cwd=str(self.agentDir),
            env=env,
        )
        self.subprocess.set_exit_callback(self._agent_on_exit)


def init_class():
    global cfg

    cfg = pkconfig.init(
        parallel_slots=(1, int, 'max parallel slots'),
        sequential_slots=(1, int, 'max sequential slots'),
    )
    return LocalDriver.init_class()


class _Slot(PKDict):

    available = PKDict()
    in_use = PKDict()

    @classmethod
    async def allocate(cls, kind):
        self = await cls.available[kind].get()
        self.in_use[self.kind].append(self)
        return self

    def free(self):
        self.in_use[self.kind].remove(self)
        self.available[self.kind].put_nowait(self)

    @classmethod
    def init_kind(cls, kind):
        q = cls.available[kind] = tornado.queues.Queue()
        for _ in range(cfg[kind + '_slots']):
            q.put_nowait(_Slot(kind=kind))
        cls.in_use[kind] = []
