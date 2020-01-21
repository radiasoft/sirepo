# -*- coding: utf-8 -*-
"""Base for drivers

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern import pkconfig, pkio, pkinspect, pkcollections, pkconfig, pkjson
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdlog, pkdc, pkdexc
from sirepo import job
import collections
import importlib
import inspect
import pykern.pkio
import sirepo.srdb
import tornado.gen
import tornado.ioloop
import tornado.locks


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


class DriverBase(PKDict):

    __instances = PKDict()

    def __init__(self, req):
        super().__init__(
            _agentId=job.unique_key(),
            _agent_starting=False,
            _agent_start_lock=tornado.locks.Lock(),
            _slot_alloc_time=None,
            kind=req.kind,
            ops=PKDict(),
            slot_num=None,
            uid=req.content.uid,
            _websocket=None,
            _websocket_ready=tornado.locks.Event(),
#TODO(robnagler) https://github.com/radiasoft/sirepo/issues/2195
        )
        # Drivers persist for the life of the program so they are never removed
        self.__instances[self._agentId] = self
        pkdlog(
            'class={} agentId={_agentId} kind={kind} uid={uid}',
            self.__class__.__name__,
            **self
        )

    def destroy_op(self, op):
        self.ops.pkdel(op.opId)

    @classmethod
    def init_slot_q(cls, maxsize):
        res = tornado.queues.Queue(maxsize=maxsize)
        for i in range(1, maxsize + 1):
            res.put_nowait(i)
        return res

    async def kill(self):
        if not self._websocket:
            # if there is no websocket then we don't know about the agent
            # so we can't do anything
            return
        # hopefully the agent is nice and listens to the kill
        self._websocket.write_message(PKDict(opName=job.OP_KILL))

    def get_supervisor_uri(self):
        return inspect.getmodule(self).cfg.supervisor_uri

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
                self.get_supervisor_uri(),
                job.LIB_FILE_URI,
                op.lib_dir_symlink.basename,
            ),
            libFileList=[f.basename for f in d.listdir()],
        )

    def op_was_sent(self, op):
        """Is the op in ops

        Args:
            op (job_supervisor._Op): what to check
        Returns:
            bool: true if in ops
        """
        return op in self.ops

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

    async def prepare_send(self, op):
        """Sends the op

        Returns:
            bool: True if the op was actually sent
        """
        if not self._websocket_ready.is_set():
            await self._agent_start(op)
            await self._websocket_ready.wait()
            raise job_supervisor.Awaited()
        if self.run_scheduler(try_op=op):
            raise job_supervisor.Awaited()

   def send(self, op):
        pkdlog(
            'op={} agentId={} opId={} runDir={}',
            op.opName,
            self._agentId,
            op.opId,
            op.msg.get('runDir')
        )
        op.start_timer()
        self._websocket.write_message(pkjson.dump_bytes(op.msg))
        self.ops.append(op)

    def slot_free(self):
        if not self.slot_num:
            return
        self.slot_q.task_done()
        self.slot_q.put_nowait(self.slot_num)
        self.slot_num = None
        self._slot_alloc_time = None

    async def slot_free_one(self):
        if self.slot_q.qsize > 0:
            # available slots, don't need to free
            return
        # least recently used, if any
        d = sorted(
            filter(
                lambda x: bool(x.slot_num and not x.ops),
                self.slot_peers(),
            ),
            key=lambda x: x._slot_alloc_time,
        )
        if d:
            d[0].slot_free()

    async def slot_ready(self):
        if self.slot_num:
            return
        try:
            self.slot_num = self.slot_q.get_nowait()
        except tornado.queues.QueueEmpty:
            self.slot_free_one()
            self.slot_num = await self.slot_q.get()
            raise job_supervisor.Awaited()
        finally:
            self._slot_alloc_time = time.time()

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

    def websocket_free(self):
        """Remove holds on all resources and remove self from data structures"""
        pkdlog('self={}', self)
        try:
            self._agent_starting = False
            self._websocket_ready.clear()
            w = self._websocket
            self._websocket = None
            if w:
                # Will not call websocket_on_close()
                w.sr_close()
            for o in list(self.ops.values()):
                o.destroy(error='websocket closed')
            self.slot_free()
            self._websocket_free()
            self.run_scheduler()
        except Exception as e:
            pkdlog('job_driver={} error={} stack={}', self, e, pkdexc())

    def websocket_on_close(self):
        self.websocket_free()

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
                SIREPO_PKCLI_JOB_AGENT_SUPERVISOR_URI=self.get_supervisor_uri().replace(
#TODO(robnagler) figure out why we need ws (wss, implicit)
                    'http',
                    'ws',
                    1,
                ) + job.AGENT_URI
            ),
            uid=self.uid,
        )

    async def _agent_start(self, op):
        async with self._agent_start_lock:
            if self._agent_starting or self._websocket_ready.is_set():
                return
            pkdlog('starting agentId={} uid={} opId={}', self._agentId, self.uid, op.opId)
            try:
                self._agent_starting = True
                # TODO(e-carlin): We need a timeout on agent starts. If an agent
                # is started but never connects we will be in the '_agent_starting'
                # state forever. After a timeout we should kill the misbehaving
                # agent and start a new one.
                await self.kill()
                # this starts the process, but _receive_alive sets it to false
                # when the agent fully starts.
                await self._do_agent_start(op)
            except Exception as e:
                pkdlog('agentId={} exception={}', self._agentId, e)
                self._agent_starting = False
                raise

    def _has_remote_agent(self):
        return False

    def _receive(self, msg):
        c = msg.content
        i = c.get('opId')
        if (
            ('opName' not in c or c.opName == job.OP_ERROR)
            or ('reply' in c and c.reply.get('state') == job.ERROR)
        ):
            pkdlog('error agentId={} msg={}', self._agentId, c)
        else:
            pkdlog('opName={} agentId={} opId={}', c.opName, self._agentId, i)
        if i:
            if 'reply' not in c:
                pkdlog('agentId={} No reply={}', self._agentId, c)
                c.reply = PKDict(state='error', error='no reply')
            if i in self.ops:
                #SECURITY: only ops known to this driver can be replied to
                self.ops[i].reply_put(c.reply)
            else:
                pkdlog('agentId={} not pending opId={} opName={}', self._agentId, i, c.opName)
        else:
            getattr(self, '_receive_' + c.opName)(msg)

    def _receive_alive(self, msg):
        """Receive an ALIVE message from our agent

        Save the websocket and register self with the websocket
        """
        if self._websocket:
            if self._websocket == msg.handler:
#TODO(robnagler) do we want to run_scheduler on alive in all cases?
#                self.run_scheduler()
                # random alive message
                return
            self.websocket_free()
        self._websocket = msg.handler
        self._websocket_ready.set()
        self._websocket.sr_driver_set(self)
#TODO(robnagler) do we want to run_scheduler on alive in all cases?
        self.run_scheduler()

    def _receive_error(self, msg):
#TODO(robnagler) what does this mean? Just a way of logging? Document this.
        pkdlog('agentId={} msg={}', self._agentId, msg)

    def _websocket_free(self):
        pass

def get_instance(req, jobRunMode):
    if jobRunMode == job.SBATCH:
        return _CLASSES[job.SBATCH].get_instance(req)
    return _DEFAULT_CLASS.get_instance(req)


def init():
    global cfg, _CLASSES, _DEFAULT_CLASS
    assert not cfg
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
