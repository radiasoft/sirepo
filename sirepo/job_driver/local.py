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

    module_name = 'local' # TODO(e-carlin): is this used anywhere?

    slots = PKDict()

    def __init__(self, req, space):
        super().__init__(req, space)
        self.update(
            _agentDir=pkio.py_path(req.content.userDir).join('agent-local', self._agentId),
        )
        self.instances[self._kind].append(self)
        tornado.ioloop.IOLoop.current().spawn_callback(self._agent_start)

    def kill(self):
        if 'subprocess' not in self:
            return
        self.subprocess.proc.terminate()
        self.kill_timeout = tornado.ioloop.IOLoop.current().call_later(
            _KILL_TIMEOUT_SECS,
            self.subprocess.proc.kill,
        )

    def terminate(self):
        if 'subprocess' in self:
            self.subprocess.proc.kill()

    def _agent_on_exit(self, returncode):
        pkcollections.unchecked_del(self, 'subprocess')
        self._free()

    async def _agent_start(self):
        pkio.mkdir_parent(self._agentDir)
#TODO(robnagler) SECURITY strip environment
        env = PKDict(os.environ).pkupdate(
            PYENV_VERSION='py3',
#TODO(robnagler) cascade from py test, not explicitly
            PYKERN_PKDEBUG_CONTROL='.',
            PYKERN_PKDEBUG_OUTPUT='/dev/tty',
            PYKERN_PKDEBUG_REDIRECT_LOGGING='1',
            PYKERN_PKDEBUG_WANT_PID_TIME='1',
            SIREPO_PKCLI_JOB_AGENT_AGENT_ID=self._agentId,
            SIREPO_PKCLI_JOB_AGENT_SUPERVISOR_URI=self._supervisor_uri,
        )
        self.subprocess = tornado.process.Subprocess(
            ['pyenv', 'exec', 'sirepo', 'job_agent'],
            cwd=str(self._agentDir),
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
    return LocalDriver.init_class(cfg)
