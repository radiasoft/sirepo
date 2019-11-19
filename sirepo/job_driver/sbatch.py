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
        try:
            c = paramiko.SSHClient()
            c.load_system_host_keys()
            c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            # TODO(e-carlin): username and pass from GUI
            c.connect(cfg.nersc_uri, username='vagrant', password='vagrant')
            cmd, f , _ = self._subprocess_cmd_stdin_env()
            s, o, _ = c.exec_command(' '.join(cmd))
            s.write(f.read())
            # TODO(e-carlin): were not reading stdout or stderr
            # for development reading stderr could be helpful
            # for production should stdout and stderr be re-directed to /dev/null?
        finally:
            c.close()


def init_class():
    global cfg

    cfg = pkconfig.init(
        nersc_uri=('v2.radia.run', str, 'ssh uri for nersc'),
    )
    return SBatchDriver
