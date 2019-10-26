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
    global cfg

    cfg = pkconfig.init(
        parallel_slots=(1, int, 'max parallel slots'),
        sequential_slots=(1, int, 'max sequential slots'),
    )
    return LocalDriver.init_class()


class LocalDriver(job_driver.DriverBase):

    module_name = 'local'

    users = pkcollections.Dict()

    def __init__(self, req, slot):
        super().__init__(req)
        self.update(
            agentDir=simulation_db.user_dir_name(self.uid).join('agent-local', selfId),
            kind=slot.kind,
            ops=PKDict(),
            slot=slot,
        )
        self.users[slot.kind][self.uid] = self
        tornado.ioloop.IOLoop.current().spawn_callback(self._start)

    @classmethod
    async def allocate(cls, kind, req):
        return cls.users[kind].get(req.content.uid) or cls(req, await _Slot.allocate(kind))

    def free(self):
        del self.users[self.kind][self.uid]
        super().free(self)

    def websocket_on_close(self):
        if 'websocket' in self:
            del self['websocket']
        for o in self.ops.values():
            o.reply(PKDict(state=job.ERROR, error='agent closed websocket'))

#TODO(robnagler) for the local driver, we might want to kill the process (SIGKILL),
#   because there would be no reason for the websocket to disappear on its own.

    @classmethod
    async def send(cls, req, kwargs):
        self = await cls.allocate(cls._kind(req, kwargs), req)
        o = Op(
            opName=kwargs.opName,
            msg=PKDict(kwargs),
            req=req,
        )
        self.ops[o.msg.opId] = o
        return await o.send(self)

    @classmethod
    def init_class(cls):
        for k in cls.KINDS:
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

    def _kind(cls, req, kwargs):
        if req.computeJob.isParallel and kwargs.opName != job.OP_ANALYSIS:
            return job.PARALLEL
        return job.SEQUENTIAL

    def _on_exit(self, returncode):
        pkcollections.unchecked_del(self, 'subprocess')
        k = self.get('kill_timeout')
        if k:
            del self['kill_timeout']
            tornado.ioloop.IOLoop.current().remove_timeout(k)
        w = self.get('websocket')
        if w:
            del self['websocket']
            s = w.close()
            self.websocket_on_close()
        self.slot.free(self)
        self.slot = None
        self.free()

    async def _receive(self, msg):
        c = msg.content
        if 'opId' in c:
            o = self.ops[c.opId]
            del self.ops[c.opId]
            self.ops[c.opId].reply(msg.output)
        else:
            getattr(self, '_receive_' + c.opName)(msg)

    def _receive_alive(self, msg):
        """Receive an ALIVE message from our agent

        Save the websocket and register self with the websocket
        """
#TODO(robnagler) existing ops will never be replied to (possibly)
        self.websocket = msg.handler
        self.websocket.sr_driver_set(self)

    async def _start(self):
#TODO(robnagler) SECURITY strip environment
        env = PKDict(os.environ).pkupdate(
            PYENV_VERSION='py3',
            PYKERN_PKDEBUG_CONTROL='.',
            PYKERN_PKDEBUG_OUTPUT='/dev/tty',
            PYKERN_PKDEBUG_REDIRECT_LOGGING='1',
            SIREPO_PKCLI_JOB_AGENT_AGENT_ID=self.agentId,
            SIREPO_PKCLI_JOB_AGENT_SUPERVISOR_URI=job_driver.cfg.supervisor_uri,
        )
        pkio.mkdir_parent(self.agentDir)
        self.subprocess = tornado.process.Subprocess(
            ['pyenv', 'exec', 'sirepo', 'job_agent'],
            cwd=str(self.agentDir),
            env=env,
        )
        self.subprocess.set_exit_callback(self._on_exit)


class Op(PKDict):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.msg.update(
            opId=job.unique_key(),
            opName=self.opName,
        )

    async def reply(self, output):
        self.reply_q.put_nowait(output)

    async def send(self, driver):
        driver.write_message(pkjson.dump_bytes(self.msg))
        q = self.reply_q = tornado.queues.Queue()
        return await q.get()


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
