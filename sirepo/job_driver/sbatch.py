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
import paramiko
import sirepo.srdb
import tornado.ioloop

cfg = None

class SBatchDriver(job_driver.DriverBase):

    instances = PKDict()

    def __init__(self, req):
        super().__init__(req)
        self.update(
            _agentExecDir=pkio.py_path(req.content.userDir).join(
                'agent-nersc', self._agentId),
        )
        self.instances[self.uid] = self
        pkio.mkdir_parent(self._agentExecDir) # TODO(e-carlin): cleanup these dirs
        tornado.ioloop.IOLoop.current().spawn_callback(self._agent_start)

    @classmethod
    async def get_instance(cls, req):
        u = req.content.uid
        return cls.instances.pksetdefault(
            u,
            lambda: cls(req)
        )[u]

    def get_ops_with_send_allocation(self):
        """
# TODO(e-carlin):
1 at a time:
    - single core compute jobs
unlimited at a time:
    - everything else

The agent will need to change to support > 1 of the same jid at once
        """
        return super().get_ops_with_send_allocation()

    @classmethod
    def run_scheduler(cls, driver):
        for d in cls.instances.values():
            if not d.websocket:
                continue
            ops_with_send_alloc = d.get_ops_with_send_allocation()
            for o in ops_with_send_alloc:
                assert o.opId not in d.ops_pending_done
                d.ops_pending_send.remove(o)
                d.ops_pending_done[o.opId] = o
                o.send_ready.set()

    async def _agent_start(self):
        async with asyncssh.connect(
            'v2.radia.run',
            username='vagrant',
            password='vagrant'
        ) as c:
            cmd, f , _ = self._subprocess_cmd_stdin_env()
            pkdp(0)
            async with c.create_process('setsid ' + ' '.join(cmd)) as p:
                a = f.read().decode('utf-8')
                p.stdin.write(a +'&') # TODO(e-carlin): docs say it accespts bytes. exceptions say otherwise?
                p.stdin.write('disown') # TODO(e-carlin): make sure this works
                p.stdin.write_eof()
                # TODO(e-carlin): this blocks forever. why?
                pkdp(1)
                pkdp(await p.stdout.read())
                pkdp(2)
                pkdp(await p.stderr.read())
                pkdp(3)

def init_class():
    global cfg

    cfg = pkconfig.init(
        nersc_uri=('v2.radia.run', str, 'ssh uri for nersc'),
    )
    return SBatchDriver
