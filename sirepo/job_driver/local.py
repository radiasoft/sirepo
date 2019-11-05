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
import collections
import os
import tornado.ioloop
import tornado.queues
import tornado.process


_KILL_TIMEOUT_SECS = 3

cfg = None


class LocalDriver(job_driver.DriverBase):

    instances = PKDict()

    module_name = 'local'

    slots = PKDict()

    def __init__(self, req, space):
        super().__init__(req)
        self.update(
            agentDir=pkio.py_path(req.content.userDir).join('agent-local', self.agentId),
            kind=space.kind,
            space=space,
        )
        self.instances[self.kind].append(self)
        tornado.ioloop.IOLoop.current().spawn_callback(self._agent_start)

    @classmethod
    async def get_instance(cls, req):
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
        for d in cls.instances[req.kind]:
            if d.uid == req.content.uid:
                return d
        return cls(req, await _Space.allocate(req.kind))

    @classmethod
    def init_class(cls):
        for k in job.KINDS:
            cls.slots[k] = PKDict(
                in_use=0,
                total=cfg[k + '_slots'],
            )
            cls.instances[k] = []
            _Space.init_kind(k)
        return cls

    def kill(self):
        if 'subprocess' not in self:
            return
        self.subprocess.proc.terminate()
        self.kill_timeout = tornado.ioloop.IOLoop.current().call_later(
            _KILL_TIMEOUT_SECS,
            self.subprocess.proc.kill,
        )

    def get_ops_pending_done_types(self):
            d = collections.defaultdict(int)
            for v in self.ops_pending_done.values():
                d[v.msg.opName] += 1
            return d

    def get_ops_with_send_allocation(self):
        """Get ops that could be sent assuming outside requirements are met.

        Outside requirements are an alive websocket connection and the driver
        having a slot.
        """
        r = []
        t = self.get_ops_pending_done_types()
        for o in self.ops_pending_send:
            if (o.msg.opName in t
                and t[o.msg.opName] > 0
            ):
                continue
            assert o.opId not in self.ops_pending_done
            t[o.msg.opName] += 1
            r.append(o)
        return r

    @classmethod
    def free_slots(cls, kind):
        for d in cls.instances[kind]:
            if d.has_slot and not d.ops_pending_send:
                cls.slots[kind].in_use -= 1

# TODO(e-carlin): Take in a arg of driver and start the loop from the index
# of that driver. Doing so enables fair scheduling. Otherwise user at start of
# list always has priority
    @classmethod
    def run_scheduler(cls, kind):
        cls.free_slots(kind)
        for d in cls.instances[kind]:
            ops_with_send_alloc = d.get_ops_with_send_allocation()
            if not ops_with_send_alloc:
                continue
            if ((not d.has_slot and cls.slots[kind].in_use >= cls.slots[kind].total)
                or not d.has_ws
            ):
                continue
            if not d.has_slot:
                # if the driver doesn't have a slot then assign the slot to it
                d.has_slot = True
                cls.slots[kind].in_use += 1
            for o in ops_with_send_alloc:
                assert o.opId not in d.ops_pending_done
                d.ops_pending_send.remove(o)
                d.ops_pending_done[o.opId] = o
                o.send_ready.set()


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

    def _free(self):
        k = self.pkdel('kill_timeout')
        if k:
            tornado.ioloop.IOLoop.current().remove_timeout(k)
        super()._free()


def init_class():
    global cfg

    cfg = pkconfig.init(
        parallel_slots=(1, int, 'max parallel slots'),
        sequential_slots=(1, int, 'max sequential slots'),
    )
    return LocalDriver.init_class()

class _Space(PKDict):
    """If a driver has a space then they have an alive agent but may not be
    actively performing an op.
    """

    in_use = PKDict()

    @classmethod
    async def allocate(cls, kind):
        self = _Space(kind=kind)
        self.in_use[self.kind].append(self)
        return self

    @classmethod
    def init_kind(cls, kind):
        cls.in_use[kind] = []