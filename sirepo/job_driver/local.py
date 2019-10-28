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
from sirepo import simulation_db
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
            agentDir=simulation_db.user_dir_name(self.uid).join('agent-local', selfId),
            kind=slot.kind,
            slot=slot,
        )
        self.users[self.kind][self.uid] = self
        tornado.ioloop.IOLoop.current().spawn_callback(self._agent_start)

    @classmethod
    async def allocate(cls, req):
        return cls.users[kind].get(req.content.uid) or cls(req, await _Slot.allocate(req.kind))

    def _free(self):
        k = self.pkdel('kill_timeout')
        if k:
            tornado.ioloop.IOLoop.current().remove_timeout(k)
        self.slot.free(self)
        self.slot = None
        del self.users[self.kind][self.uid]
        super()._free(self)

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
        return (await cls.allocate(req))._send(req, kwargs)

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
            PYKERN_PKDEBUG_CONTROL='.',
            PYKERN_PKDEBUG_OUTPUT='/dev/tty',
            PYKERN_PKDEBUG_REDIRECT_LOGGING='1',
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

    def free(self):
        self.in_use[self.kind].remove(self)
        self.available[self.kind].put_nowait(self)

    @classmethod
    def init_kind(cls, kind):
        q = cls.available[kind] = tornado.queues.Queue()
        for _ in range(cfg[kind + '_slots']):
            q.put_nowait(_Slot(kind=kind))
        cls.in_use[kind] = []
