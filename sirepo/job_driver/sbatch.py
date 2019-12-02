# -*- coding: utf-8 -*-
"""TODO(e-carlin): Doc

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkconfig
from pykern import pkio
from pykern import pkjinja
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp
from sirepo import job
from sirepo import job_driver
import asyncssh
import sirepo.srdb
import tornado.ioloop

cfg = None

_KNOWN_HOSTS = None

class SBatchDriver(job_driver.DriverBase):

    instances = PKDict()

    def __init__(self, req):
        super().__init__(req)
        m = req.content
#TODO(robnagler) read a db for an sbatchuser
        self.__user = 'nagler'
        self.__srdb_root = cfg.srdb_root.format(sbatchUser=self.__user)
        self.instances[self.uid] = self
        tornado.ioloop.IOLoop.current().spawn_callback(self._agent_start)

    @classmethod
    async def get_instance(cls, req):
        u = req.content.uid
        return cls.instances.pksetdefault(u, lambda: cls(req))[u]

    @classmethod
    def init_class(cls):
        return cls

    async def kill(self):
        if not self.websocket:
            # if there is no websocket then we don't know about the agent
            # so we can't do anything
            return
        # hopefully the agent is nice and listens to the kill
        self.websocket.write_message(PKDict(opName=job.OP_KILL))

    def run_scheduler(self, exclude_self=False):
        for d in self.instances.values():
            if exclude_self and d == self:
                continue
            for o in d.get_ops_with_send_allocation():
                assert o.opId not in d.ops_pending_done
                d.ops_pending_send.remove(o)
                d.ops_pending_done[o.opId] = o
#TODO(robnagler) encapsulation is incorrect. Superclass should make
# decisions about send_ready.
                o.send_ready.set()

    async def send(self, op):
        m = self.msg
        op.msg.runDir = '/'.join(self._srdb_root, m.simulationType, m.computeJid)
        op.msg.sbatchCores = 32
        op.msg.sbatchHours = 1
        op.msg.shifterImage = cfg.get('shifter_image', '')
        return super().send(op)

    async def _agent_start(self):
        # TODO(e-carlin): handle cori ssh key. Currently this defaults
        # to using the keys in ~/.ssh/known_hosts
        async with asyncssh.connect(
            cfg.host,
#TODO(robnagler) add password management
            username=self._user,
            password=totp(),
            known_hosts=_KNOWN_HOSTS,
        ) as c:
            script = f'''#!/bin/bash
set -e
mkdir -p '{self._srdb_root}'
cd '{self._srdb_root}'
{self._agent_env()}
setsid {cfg.sirepo_cmd} job_agent >& agent.log'''
            async with c.create_process(pkdp(' '.join(cmd))) as p:
                o, e = await p.communicate(input=script)
                assert o == '' and e == '', \
                    'stdout={} stderr={}'.format(o, e)
            stdin.close()

    def _websocket_free(self):
        self.run_scheduler(exclude_self=True)
        self.instances.pkdel(self.uid)


def init_class():
    global cfg, _KNOWN_HOSTS

    cfg = pkconfig.init(
        host=pkconfig.Required(str, 'host name for slum controller'),
        host_key=pkconfig.Required(str, 'host key'),
        shifter_image=(None, str, 'needed if using Shifter'),
        sirepo_cmd=pkconfig.Required(str, 'how to run sirepo'),
        srdb_root=pkconfig.Required(_cfg_srdb_root, 'where to run job_agent, must include {sbatch_user}'),
    )
    _KNOWN_HOSTS = (
        cfg.host_key if cfg.host in cfg.host_key
        else '{} {}'.format(cfg.host, cfg.host_key)
    ).encode('ascii')
    return SBatchDriver.init_class()


def _cfg_srdb_root(value):
    assert '{sbatch_user}' in value, \
        'must include {sbatch_user} in string'
    return value
