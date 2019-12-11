# -*- coding: utf-8 -*-
"""TODO(e-carlin): Doc

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkconfig
from pykern import pkio
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdlog
from sirepo import job
from sirepo import job_driver
from sirepo import util
import asyncssh
import tornado.ioloop

cfg = None

_KNOWN_HOSTS = None


class SbatchDriver(job_driver.DriverBase):

    instances = PKDict()

    def __init__(self, req):
        super().__init__(req)
#TODO(robnagler) read a db for an sbatch_user
        self._user = cfg.user
        self._srdb_root = cfg.srdb_root.format(sbatch_user=self._user)
        self.instances[self.uid] = self

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
        m = op.msg
        m.runDir = '/'.join((str(self._srdb_root), m.simulationType, m.computeJid))
        if op.opName == job.OP_RUN:
            assert m.sbatchHours
            if cfg.cores:
                # override for dev
                m.sbatchCores = cfg.cores
            m.mpiCores = m.sbatchCores
        m.shifterImage = cfg.shifter_image
        return await super().send(op)

    def _agent_env(self):
        return super()._agent_env(
            env=PKDict(
                SIREPO_SRDB_ROOT=self._srdb_root,
            )
        )

    async def _agent_start(self, msg):
        if 'password' not in msg or 'username' not in msg:
            self._raise_sbatch_login_srexception('no-creds', msg)
        self._agent_starting = True
        try:
            async with asyncssh.connect(
                cfg.host,
    #TODO(robnagler) add password management
                username=self._user, # TODO(e-carlin): msg.get('email')
                password=msg.get('password'),
                # password=self._user if self._user == 'vagrant' else totp(),
                known_hosts=_KNOWN_HOSTS,
            ) as c:
                script = f'''#!/bin/bash
{self._agent_start_dev()}
set -e
mkdir -p '{self._srdb_root}'
cd '{self._srdb_root}'
{self._agent_env()}
setsid {cfg.sirepo_cmd} job_agent >& job_agent.log &
disown
'''
                async with c.create_process('/bin/bash') as p:
                    o, e = await p.communicate(input=script)
                    if o or e:
                        raise AssertionError(
                            'agentId={} stdout={} stderr={}'.format(
                                self._agentId,
                                o,
                                e
                            )
                        )
        except Exception as e:
            self._agent_starting = False
            pkdlog(
                'agentId={} exception={}',
                self._agentId,
                e,
            #TODO(robnagler) try to read the job_agent.log
            )
            if isinstance(e, asyncssh.misc.PermissionDenied):
                # TODO(e-carlin): only some fields from msg
                self._raise_sbatch_login_srexception('invalid-creds', msg)
            raise

    def _agent_start_dev(self):
        if not pkconfig.channel_in('dev'):
            return ''
        res = '''
pkill -f 'sirepo job_agent' >& /dev/null || true
scancel -u $USER >& /dev/null || true
'''
        if cfg.shifter_image:
            res += '''
(cd ~/src/radiasoft/sirepo && git pull -q) || true
(cd ~/src/radiasoft/pykern && git pull -q) || true
'''
        return res

    def _raise_sbatch_login_srexception(self, reason, msg):
        raise util.SRException(
            'sbatchLogin',
            PKDict(
                isModal=True,
                reason=reason,
                simulationId=msg.simulationId,
                simulationType=msg.simulationType,
                report=msg.computeModel,
                host=cfg.host,
            ),
        )

    def _websocket_free(self):
        self.run_scheduler(exclude_self=True)
        self.instances.pkdel(self.uid)


def init_class():
    global cfg, _KNOWN_HOSTS

    cfg = pkconfig.init(
        host=pkconfig.Required(str, 'host name for slum controller'),
        host_key=pkconfig.Required(str, 'host key'),
        user=('vagrant', str, 'temporary user config'),
        cores=(None, int, 'dev cores config'),
        shifter_image=(None, str, 'needed if using Shifter'),
        sirepo_cmd=pkconfig.Required(str, 'how to run sirepo'),
        srdb_root=pkconfig.Required(_cfg_srdb_root, 'where to run job_agent, must include {sbatch_user}'),
    )
    _KNOWN_HOSTS = (
        cfg.host_key if cfg.host in cfg.host_key
        else '{} {}'.format(cfg.host, cfg.host_key)
    ).encode('ascii')
    return SbatchDriver.init_class()


def _cfg_srdb_root(value):
    assert '{sbatch_user}' in value, \
        'must include {sbatch_user} in string'
    return value


import base64
import hashlib
import hmac
import os
import struct
import sys
import time

def totp():
    return pkio.py_path(os.getenv('A')).read().strip() + _totp(pkio.py_path(os.getenv('B')).read().strip())

def _hotp(secret, counter):
    secret  = base64.b32decode(secret)
    counter = struct.pack('>Q', counter)
    hash   = hmac.new(secret, counter, hashlib.sha1).digest()
    offset = hash[19] & 0xF
    return (struct.unpack(">I", hash[offset:offset + 4])[0] & 0x7FFFFFFF) % 1000000


def _totp(secret):
    return '{:06d}'.format(int(_hotp(secret, int(time.time()) // 30)))
