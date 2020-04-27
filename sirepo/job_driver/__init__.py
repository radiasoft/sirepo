# -*- coding: utf-8 -*-
"""Base for drivers

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern import pkconfig, pkio, pkinspect, pkcollections, pkconfig, pkjson
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdlog, pkdc, pkdexc, pkdformat
from sirepo import job
import asyncio
import importlib
import pykern.pkio
import sirepo.srdb
import sirepo.tornado
import time
import tornado.gen
import tornado.ioloop
import tornado.locks
import tornado.queues


KILL_TIMEOUT_SECS = 3

#: map of driver names to class
_CLASSES = None

#: default class when not determined by request
_DEFAULT_CLASS = None

_DEFAULT_MODULE = 'local'

cfg = None


class AgentMsg(PKDict):

    async def receive(self):
        # Agent messages do not block the supervisor
        DriverBase.receive(self)


def assign_instance_op(req, jobRunMode, op):
    if jobRunMode == job.SBATCH:
        res = _CLASSES[job.SBATCH].get_instance(req)
    else:
        res = _DEFAULT_CLASS.get_instance(req)
    assert req.content.uid == res.uid, \
        'req.content.uid={} is not same as db.uid={} for jid={}'.format(
            req.content.uid,
            res.uid,
            req.content.computeJid,
        )
    op.driver = res
    op.driver.ops[op.opId] = op
    op.op_slot = None


class DriverBase(PKDict):

    __instances = PKDict()

    _AGENT_STARTING_SECS = 5

    def __init__(self, req):
        super().__init__(
            cpu_slot=None,
            driver_details=PKDict({'type': self.__class__.__name__}),
            kind=req.kind,
            ops=PKDict(),
            op_q=PKDict({
                #TODO(robnagler) sbatch could override OP_RUN, but not OP_ANALYSIS
                # because OP_ANALYSIS touches the directory sometimes. Reasonably
                # there should only be one OP_ANALYSIS running on an agent at one time.
                job.OP_RUN: self.init_q(1),
                job.OP_ANALYSIS: self.init_q(1),
            }),
            uid=req.content.uid,
            _agentId=job.unique_key(),
            _agent_start_lock=tornado.locks.Lock(),
            _agent_starting_timeout=None,
            _cpu_slot_q_lock=tornado.locks.Lock(),
            _cpu_slot_alloc_time=None,
            _websocket=None,
            _websocket_ready=tornado.locks.Event(),
#TODO(robnagler) https://github.com/radiasoft/sirepo/issues/2195
        )
        # Drivers persist for the life of the program so they are never removed
        self.__instances[self._agentId] = self
        pkdlog('{}', self)

    def cpu_slot_free(self):
        if not self.cpu_slot:
            return
        self.cpu_slot_q.task_done()
        self.cpu_slot_q.put_nowait(self.cpu_slot)
        self.cpu_slot = None
        self._cpu_slot_alloc_time = None

    def cpu_slot_free_one(self):
        if self.cpu_slot_q.qsize() > 0:
            # available slots, don't need to free
            return
        # This is not fair scheduling, but good enough for now.
        # least recently used and not in use
        d = sorted(
            filter(
                lambda x: bool(x.cpu_slot and not x.ops),
                self.cpu_slot_peers(),
            ),
            key=lambda x: x._cpu_slot_alloc_time,
        )
        if d:
            d[0].cpu_slot_free()

    async def cpu_slot_ready(self):
        if self.cpu_slot:
            return
        try:
            self.cpu_slot = self.cpu_slot_q.get_nowait()
            self._cpu_slot_alloc_time = time.time()
        except tornado.queues.QueueEmpty:
            self.cpu_slot_free_one()
            pkdlog('{} await cpu_slot_q_lock', self)
            async with self._cpu_slot_q_lock.acquire():
                if self.cpu_slot:
                    raise job_supervisor.Awaited()
                pkdlog('{} await cpu_slot_q.get()', self)
                self.cpu_slot = await self.cpu_slot_q.get()
                self._cpu_slot_alloc_time = time.time()
                raise job_supervisor.Awaited()

    def destroy_op(self, op):
        """Clear our op and (possibly) free cpu slot"""
        self.ops.pkdel(op.opId)
        if not self.ops:
            # might free our cpu slot if no other ops
            self.cpu_slot_free_one()
        if op.op_slot:
            q = self.op_q[op.opName]
            q.task_done()
            q.put_nowait(op.op_slot)
            op.op_slot = None

    def free_resources(self, internal_error=None):
        """Remove holds on all resources and remove self from data structures"""
        pkdlog('{} internal_error={}', self, internal_error)
        try:
            self._agent_starting_done()
            self._websocket_ready.clear()
            w = self._websocket
            self._websocket = None
            if w:
                # Will not call websocket_on_close()
                w.sr_close()
            for o in list(self.ops.values()):
                o.destroy(internal_error=internal_error)
            self.cpu_slot_free()
            self._websocket_free()
        except Exception as e:
            pkdlog('{} error={} stack={}', self, e, pkdexc())

    @classmethod
    def init_q(cls, maxsize):
        res = sirepo.tornado.Queue(maxsize=maxsize)
        for i in range(1, maxsize + 1):
            res.put_nowait(i)
        return res

    async def kill(self):
        raise NotImplementedError(
            'DriverBase subclasses need to implement their own kill',
        )

    def make_lib_dir_symlink(self, op):
        if not self._has_remote_agent():
            return
        m = op.msg
        d = pykern.pkio.py_path(m.simulation_lib_dir)
        op.lib_dir_symlink = job.LIB_FILE_ROOT.join(
            job.unique_key()
        )
        op.lib_dir_symlink.mksymlinkto(d, absolute=True)
        m.pkupdate(
            libFileUri=job.supervisor_file_uri(
                self.cfg.supervisor_uri,
                job.LIB_FILE_URI,
                op.lib_dir_symlink.basename,
            ),
            libFileList=[f.basename for f in d.listdir()],
        )

    async def op_ready(self, op):
        """Only one op of each type allowed

        """
        n = op.opName
        if n in (job.OP_CANCEL, job.OP_KILL):
            return
        if n == job.OP_SBATCH_LOGIN:
            l = [o for o in self.ops.values() if o.opId != op.opId]
            assert not l, \
                'received {} but have other ops={}'.format(op, l)
            return
        if op.op_slot:
            return
        q = self.op_q[n]
        try:
            op.op_slot = q.get_nowait()
        except tornado.queues.QueueEmpty:
            pkdlog('{} {} await op_q.get()', self, op)
            op.op_slot = await q.get()
            raise job_supervisor.Awaited()

    def pkdebug_str(self):
        return pkdformat(
            '{}(a={:.4} k={} u={:.4} c={} {})',
            self.__class__.__name__,
            self._agentId,
            self.kind,
            self.uid,
            self.get('cpu_slot'),
            list(self.ops.values()),
        )

    async def prepare_send(self, op):
        """Sends the op

        Returns:
            bool: True if the op was actually sent
        """
        if not self._websocket_ready.is_set():
            await self._agent_start(op)
            pkdlog('{} {} await _websocket_ready', self, op)
            await self._websocket_ready.wait()
            raise job_supervisor.Awaited()
        await self.cpu_slot_ready()
        # must be last, because reserves queue position of op
        # relative to other ops even it throws Awaited when the
        # op_slot is assigned.
        await self.op_ready(op)

    @classmethod
    def receive(cls, msg):
        """Receive message from agent"""
        a = cls.__instances.get(msg.content.agentId)
        if a:
            a._receive(msg)
            return
        pkdlog('unknown agent, sending kill; msg={}', msg)
        try:
            msg.handler.write_message(PKDict(opName=job.OP_KILL))
        except Exception as e:
            pkdlog('error={} stack={}', e, pkdexc())

    def send(self, op):
        pkdlog(
            '{} {} runDir={}',
            self,
            op,
            op.msg.get('runDir')
        )
        self._websocket.write_message(pkjson.dump_bytes(op.msg))

    @classmethod
    async def terminate(cls):
        for d in list(cls.__instances.values()):
            try:
#TODO(robnagler) need timeout
                await d.kill()
            except job_supervisor.Awaited:
                pass
            except Exception as e:
                # If one kill fails still try to kill the rest
                pkdlog('error={} stack={}', e, pkdexc())

    def websocket_on_close(self):
        pkdlog('{}', self)
        self.free_resources()

    def _agent_cmd_stdin_env(self, **kwargs):
        return job.agent_cmd_stdin_env(
            ('sirepo', 'job_agent', 'start'),
            env=self._agent_env(),
            **kwargs,
        )

    def _agent_env(self, env=None):
        return job.agent_env(
            env=(env or PKDict()).pksetdefault(
                PYKERN_PKDEBUG_WANT_PID_TIME='1',
                SIREPO_PKCLI_JOB_AGENT_AGENT_ID=self._agentId,
                SIREPO_PKCLI_JOB_AGENT_SUPERVISOR_URI=self.cfg.supervisor_uri.replace(
#TODO(robnagler) figure out why we need ws (wss, implicit)
                    'http',
                    'ws',
                    1,
                ) + job.AGENT_URI
            ),
            uid=self.uid,
        )

    async def _agent_start(self, op):
        if self._agent_starting_timeout:
            return
        async with self._agent_start_lock:
            if self._agent_starting_timeout or self._websocket_ready.is_set():
                return
            try:
                pkdlog('{} {} await _do_agent_start', self, op)
                # All awaits must be after this. If a call hangs the timeout
                # handler will cancel this task
                self._agent_starting_timeout = tornado.ioloop.IOLoop.current().call_later(
                    self._AGENT_STARTING_SECS,
                    self._agent_starting_timeout_handler,
                )
                # POSIT: CancelledError isn't smothered by any of the below calls
                await self.kill()
                await self._do_agent_start(op)
            except Exception as e:
                pkdlog('{} error={} stack={}', self, e, pkdexc())
                self.free_resources(internal_error='failure starting agent')
                raise

    def _agent_starting_done(self):
        if self._agent_starting_timeout:
            tornado.ioloop.IOLoop.current().remove_timeout(
                self._agent_starting_timeout
            )
            self._agent_starting_timeout = None

    def _agent_starting_timeout_handler(self):
        pkdlog('{} timeout={}', self, self._AGENT_STARTING_SECS)
        self.free_resources(internal_error='timeout waiting for agent to start')

    def _has_remote_agent(self):
        return False

    def _receive(self, msg):
        c = msg.content
        i = c.get('opId')
        if (
            ('opName' not in c or c.opName == job.OP_ERROR)
            or ('reply' in c and c.reply.get('state') == job.ERROR)
        ):
            pkdlog('{} error msg={}', self, c)
        elif c.opName == job.OP_JOB_CMD_STDERR:
            pkdlog('{} stderr from job_cmd msg={}', self, c)
            return
        else:
            pkdlog('{} opName={} o={:.4}', self, c.opName, i)
        if i:
            if 'reply' not in c:
                pkdlog('{} no reply={}', self, c)
                c.reply = PKDict(state='error', error='no reply')
            if i in self.ops:
                #SECURITY: only ops known to this driver can be replied to
                self.ops[i].reply_put(c.reply)
            else:
                pkdlog(
                    '{} not pending opName={} o={:.4}',
                    self,
                    i,
                    c.opName,
                )
        else:
            getattr(self, '_receive_' + c.opName)(msg)

    def _receive_alive(self, msg):
        """Receive an ALIVE message from our agent

        Save the websocket and register self with the websocket
        """
        self._agent_starting_done()
        if self._websocket:
            if self._websocket != msg.handler:
                pkdlog('{} new websocket', self)
                # New _websocket so bind
                self.free_resources()
        self._websocket = msg.handler
        self._websocket_ready.set()
        self._websocket.sr_driver_set(self)

    def __str__(self):
        return f'{type(self).__name__}({self._agentId:.4}, {self.uid:.4}, ops={list(self.ops.values())})'

    def _receive_error(self, msg):
#TODO(robnagler) what does this mean? Just a way of logging? Document this.
        pkdlog('{} msg={}', self, msg)

    def _websocket_free(self):
        pass


def init(job_supervisor_module):
    global cfg, _CLASSES, _DEFAULT_CLASS, job_supervisor
    assert not cfg
    job_supervisor = job_supervisor_module
    cfg = pkconfig.init(
        modules=((_DEFAULT_MODULE,), set, 'available job driver modules'),
    )
    _CLASSES = PKDict()
    p = pkinspect.this_module().__name__
    for n in cfg.modules:
        m = importlib.import_module(pkinspect.module_name_join((p, n)))
        _CLASSES[n] = m.init_class()
    _DEFAULT_CLASS = _CLASSES.get('docker') or _CLASSES.get(_DEFAULT_MODULE)
    pkdlog('modules={}', sorted(_CLASSES.keys()))


async def terminate():
    await DriverBase.terminate()
