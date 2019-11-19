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
            cmd, stdin , _ = self._subprocess_cmd_stdin_env(fork=True)
            async with c.create_process(' '.join(cmd)) as p:
                o, e = await p.communicate(input=stdin.read().decode('utf-8'))
                assert o == '' and e == '', \
                    'stdout={} stderr={}'.format(o, e)
            stdin.close()


def init_class():
    global cfg

    cfg = pkconfig.init(
        nersc_uri=('v2.radia.run', str, 'ssh uri for nersc'),
    )
    return SBatchDriver
