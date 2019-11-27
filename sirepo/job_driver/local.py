# -*- coding: utf-8 -*-
"""Runs processes on the current host

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
import sirepo.job_driver
import sirepo.srdb
import tornado.ioloop
import tornado.process
import tornado.queues

cfg = None


class LocalDriver(job_driver.DriverBase):

    instances = PKDict()

    slots = PKDict()

    def __init__(self, req):
        super().__init__(req)
        self.update(
            _agentExecDir=pkio.py_path(req.content.userDir).join(
                'agent-local', self._agentId),
            _agent_exit=tornado.locks.Event(),
        )
        self.instances[self.kind].append(self)
        tornado.ioloop.IOLoop.current().spawn_callback(self._agent_start)

    @classmethod
    async def get_instance(cls, req):
        # TODO(robnagler) need to introduce concept of parked drivers for reallocation.
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

        # TODO(robnagler) drivers are not organized by uid, because there can be more
        # than one per user, rather, we can have a list here, not just self.
        # need to have an allocation per user, e.g. 2 sequential and one 1 parallel.
        # _Slot() may have to understand this, because related to parking. However,
        # we are parking a driver so maybe that's a (local) driver mechanism
        for d in cls.instances[req.kind]:
            # SECURITY: must only return instances for authorized user
            if d.uid == req.content.uid:
                return d
        return cls(req)

    @classmethod
    def init_class(cls, cfg):
        for k in job.KINDS:
            cls.slots[k] = PKDict(
                in_use=0,
                total=cfg[k + '_slots'],
            )
        super().init_class(cfg)
        return cls

    async def kill(self):
        if 'subprocess' not in self:
            return
        pkdlog(self.subprocess.proc.pid)
        self.subprocess.proc.terminate()
        self.kill_timeout = tornado.ioloop.IOLoop.current().call_later(
            job_driver.KILL_TIMEOUT_SECS,
            self.subprocess.proc.kill,
        )
        await self._agent_exit.wait()

    @classmethod
    def free_slots(cls, kind):
        for d in cls.instances[kind]:
            if d.has_slot and not d.ops_pending_done:
                d.slot_free()
        assert cls.slots[kind].in_use > -1

    @classmethod
    def run_scheduler(cls, driver):
        cls.free_slots(driver.kind)
        try:
            i = cls.instances[driver.kind].index(driver)
        except ValueError:
            # In the _websocket_free() code we remove driver from list of
            # instances.
            i = 0
        # start iteration from index of current driver to enable fair scheduling
        for d in cls.instances[driver.kind][i:] + cls.instances[driver.kind][:i]:
            ops_with_send_alloc = d.get_ops_with_send_allocation()
            if not ops_with_send_alloc:
                continue
            if ((not d.has_slot and
                 cls.slots[driver.kind].in_use >= cls.slots[driver.kind].total
                 )
                    or not d.websocket
                ):
                continue
            if not d.has_slot:
                assert cls.slots[driver.kind].in_use < cls.slots[driver.kind].total
                d.has_slot = True
                cls.slots[driver.kind].in_use += 1
            for o in ops_with_send_alloc:
                assert o.opId not in d.ops_pending_done
                d.ops_pending_send.remove(o)
                d.ops_pending_done[o.opId] = o
                o.send_ready.set()

    def slot_free(self):
        self.slots[self.kind].in_use -= 1
        self.has_slot = False

    def terminate(self):
        if 'subprocess' in self:
            self.subprocess.proc.kill()

    def _agent_on_exit(self, returncode):
        self._agent_exit.set()
        self.pkdel('subprocess')
        k = self.pkdel('kill_timeout')
        self._agentExecDir.remove(rec=True, ignore_errors=True) # TODO(e-carlin): verify
        if k:
            tornado.ioloop.IOLoop.current().remove_timeout(k)

    async def _agent_start(self):
        cmd, stdin, env = self._subprocess_cmd_stdin_env(cwd=self._agentExecDir)
        self.subprocess = tornado.process.Subprocess(
            cmd,
            env=env,
            stdin=stdin,
        )
        stdin.close()
        self.subprocess.set_exit_callback(self._agent_on_exit)


def init_class():
    global cfg

    cfg = pkconfig.init(
        parallel_slots=(1, int, 'max parallel slots'),
        sequential_slots=(1, int, 'max sequential slots'),
    )
    return LocalDriver.init_class(cfg)
