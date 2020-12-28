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
import re
import sirepo.auth
import sirepo.events
import sirepo.simulation_db
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

#: default class when not determined by op
_DEFAULT_CLASS = None

_DEFAULT_MODULE = 'local'

cfg = None

OPS_THAT_NEED_SLOTS = frozenset((job.OP_ANALYSIS, job.OP_RUN))

_UNTIMED_OPS = frozenset((job.OP_ALIVE, job.OP_CANCEL, job.OP_ERROR, job.OP_KILL, job.OP_OK))


class AgentMsg(PKDict):

    async def receive(self):
        # Agent messages do not block the supervisor
        DriverBase.receive(self)


def assign_instance_op(op):
    m = op.msg
    if m.jobRunMode == job.SBATCH:
        res = _CLASSES[job.SBATCH].get_instance(op)
    else:
        res = _DEFAULT_CLASS.get_instance(op)
    assert m.uid == res.uid, \
        'op.msg.uid={} is not same as db.uid={} for jid={}'.format(
            m.uid,
            res.uid,
            m.computeJid,
        )
    res.ops[op.opId] = op
    return res


class DriverBase(PKDict):

    __instances = PKDict()

    _AGENT_STARTING_SECS_DEFAULT = 5

    def __init__(self, op):
        super().__init__(
            driver_details=PKDict({'type': self.__class__.__name__}),
            kind=op.kind,
            ops=PKDict(),
            #TODO(robnagler) sbatch could override OP_RUN, but not OP_ANALYSIS
            # because OP_ANALYSIS touches the directory sometimes. Reasonably
            # there should only be one OP_ANALYSIS running on an agent at one time.
            op_slot_q=PKDict({k: job_supervisor.SlotQueue() for k in OPS_THAT_NEED_SLOTS}),
            uid=op.msg.uid,
            _agentId=job.unique_key(),
            _agent_start_lock=tornado.locks.Lock(),
            _agent_starting_timeout=None,
            _sim_db_file_key=job.unique_key(),
            _idle_timer=None,
            _websocket=None,
            _websocket_ready=sirepo.tornado.Event(),
#TODO(robnagler) https://github.com/radiasoft/sirepo/issues/2195
        )
        # Drivers persist for the life of the program so they are never removed
        self.__instances[self._agentId] = self
        sirepo.events.emit(
            'supervisor_sim_db_file_key_created',
            PKDict(key=self._sim_db_file_key, uid=self.uid),
        )
        pkdlog('{}', self)

    def destroy_op(self, op):
        """Clear our op and (possibly) free cpu slot"""
        self.ops.pkdel(op.opId)
        op.cpu_slot.free()
        if op.op_slot:
            op.op_slot.free()
        if 'lib_dir_symlink' in op:
            # lib_dir_symlink is unique_key so not dangerous to remove
            pykern.pkio.unchecked_remove(op.pkdel('lib_dir_symlink'))

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
            self._websocket_free()
        except Exception as e:
            pkdlog('{} error={} stack={}', self, e, pkdexc())

    async def kill(self):
        raise NotImplementedError(
            'DriverBase subclasses need to implement their own kill',
        )

    def make_lib_dir_symlink(self, op):
        m = op.msg
        with sirepo.auth.set_user(m.uid):
            d = sirepo.simulation_db.simulation_lib_dir(m.simulationType)
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

    def op_is_untimed(self, op):
        return op.opName in _UNTIMED_OPS

    def pkdebug_str(self):
        return pkdformat(
            '{}(a={:.4} k={} u={:.4} {})',
            self.__class__.__name__,
            self._agentId,
            self.kind,
            self.uid,
            list(self.ops.values()),
        )

    async def prepare_send(self, op):
        """Sends the op

        Returns:
            bool: True if the op was actually sent
        """
        await self._agent_ready(op)
        await self._slots_ready(op)

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
                SIREPO_PKCLI_JOB_AGENT_SUPERVISOR_SIM_DB_FILE_URI=job.supervisor_file_uri(
                    self.cfg.supervisor_uri,
                    job.SIM_DB_FILE_URI,
                    sirepo.simulation_db.USER_ROOT_DIR,
                    self.uid,
                ),
                SIREPO_PKCLI_JOB_AGENT_SUPERVISOR_SIM_DB_FILE_KEY=self._sim_db_file_key,
                SIREPO_PKCLI_JOB_AGENT_AGENT_ID=self._agentId,
                SIREPO_PKCLI_JOB_AGENT_START_DELAY=self.get('_agent_start_delay', 0),
                SIREPO_PKCLI_JOB_AGENT_SUPERVISOR_URI=self.cfg.supervisor_uri.replace(
#TODO(robnagler) figure out why we need ws (wss, implicit)
                    'http',
                    'ws',
                    1,
                ) + job.AGENT_URI
            ),
            uid=self.uid,
        )

    async def _agent_ready(self, op):
        if self._websocket_ready.is_set():
            return
        await self._agent_start(op)
        pkdlog('{} {} await _websocket_ready', self, op)
        await self._websocket_ready.wait()
        pkdc('{} websocket alive', op)
        raise job_supervisor.Awaited()

    async def _agent_start(self, op):
        if self._agent_starting_timeout:
            return
        async with self._agent_start_lock:
            # POSIT: we do not have to raise Awaited(), because
            # this is the first thing an op waits on.
            if self._agent_starting_timeout or self._websocket_ready.is_set():
                return
            try:
                t = self.cfg.agent_starting_secs
                if pkconfig.channel_in_internal_test():
                    x = op.msg.pkunchecked_nested_get('data.models.dog.favoriteTreat')
                    if x:
                        x = re.search(r'agent_start_delay=(\d+)', x)
                        if x:
                            self._agent_start_delay = int(x.group(1))
                            t += self._agent_start_delay
                            pkdlog('op={} agent_start_delay={}', op, self._agent_start_delay)
                pkdlog('{} {} await _do_agent_start', self, op)
                # All awaits must be after this. If a call hangs the timeout
                # handler will cancel this task
                self._agent_starting_timeout = tornado.ioloop.IOLoop.current().call_later(
                    t,
                    self._agent_starting_timeout_handler,
                )
                # POSIT: Canceled errors aren't smothered by any of the below calls
                await self.kill()
                await self._do_agent_start(op)
            except Exception as e:
                pkdlog('{} error={} stack={}', self, e, pkdexc())
                self.free_resources(internal_error='failure starting agent')
                raise

    def _agent_starting_done(self):
        self._start_idle_timeout()
        if self._agent_starting_timeout:
            tornado.ioloop.IOLoop.current().remove_timeout(
                self._agent_starting_timeout
            )
            self._agent_starting_timeout = None

    async def _agent_starting_timeout_handler(self):
        pkdlog('{} timeout={}', self, self.cfg.agent_starting_secs)
        await self.kill()
        self.free_resources(internal_error='timeout waiting for agent to start')

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

    async def _slots_ready(self, op):
        """Only one op of each type allowed"""
        n = op.opName
        if n in (job.OP_CANCEL, job.OP_KILL):
            return
        if n == job.OP_SBATCH_LOGIN:
            l = [o for o in self.ops.values() if o.opId != op.opId]
            assert not l, \
                'received {} but have other ops={}'.format(op, l)
            return
        await op.op_slot.alloc('Waiting for another simulation to complete')
        await op.run_dir_slot.alloc('Waiting for access to simulation state')
        # once job-op relative resources are acquired, ask for global resources
        # so we only acquire on global resources, once we know we are ready to go.
        await op.cpu_slot.alloc('Waiting for CPU resources')

    def _start_idle_timeout(self):
        async def _kill_if_idle():
            self._idle_timer = None
            if not self.ops:
                pkdlog('{}', self)
                await self.kill()
            else:
                self._start_idle_timeout()

        if not self._idle_timer:
            self._idle_timer = tornado.ioloop.IOLoop.current().call_later(
                cfg.idle_check_secs,
                _kill_if_idle,
            )

    def _websocket_free(self):
        pass


def init(job_supervisor_module):
    global cfg, _CLASSES, _DEFAULT_CLASS, job_supervisor
    assert not cfg
    job_supervisor = job_supervisor_module
    cfg = pkconfig.init(
        modules=((_DEFAULT_MODULE,), set, 'available job driver modules'),
        idle_check_secs=(1800, pkconfig.parse_seconds, 'how many seconds to wait between checks'),
    )
    _CLASSES = PKDict()
    p = pkinspect.this_module().__name__
    for n in cfg.modules:
        m = importlib.import_module(pkinspect.module_name_join((p, n)))
        _CLASSES[n] = m.CLASS.init_class(job_supervisor)
    _DEFAULT_CLASS = _CLASSES.get('docker') or _CLASSES.get(_DEFAULT_MODULE)
    pkdlog('modules={}', sorted(_CLASSES.keys()))


async def terminate():
    await DriverBase.terminate()
