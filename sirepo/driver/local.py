# -*- coding: utf-8 -*-
"""TODO(e-carlin): Doc

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkcollections
from pykern import pkconfig
from pykern.pkdebug import pkdp, pkdlog, pkdexc, pkdc
from sirepo import driver
from sirepo import job
from sirepo import job_supervisor
import os
import sirepo.mpi
import tornado.process
import functools

# TODO(e-carlin): cfg should be at bottom like in other modules. Except that
# class LocalDriver needs it which means it has to be declared before it
cfg = pkconfig.init(
    job_server_ws_uri=(
        job.cfg.job_server_ws_uri,
        str,
        'uri to reach the job server for websocket connections',
    ),
    parallel_slots=(
        1, int, 'total number of parallel slots'
    ),
    sequential_slots=(
        1, int, 'total number of sequential slots'
    ),
)

class LocalDriver(driver.DriverBase):
    resources = pkcollections.Dict(
        parallel=pkcollections.Dict(
            drivers=[],
            slots=pkcollections.Dict(
                total=cfg.parallel_slots,
                in_use=0,
            )
        ),
        sequential=pkcollections.Dict(
            drivers=[],
            slots=pkcollections.Dict(
                total=cfg.sequential_slots,
                in_use=0,
            )
        ),
    )

    def __init__(self, uid, resource_class):
        super(LocalDriver, self).__init__(uid, resource_class)
        self._agent = _LocalAgent(self.agent_id)

        # TODO(e-carlin): This is used to get stats about drivers as the code
        # is running. Only useful when closely debugging code. Probably delete.
        # tornado.ioloop.IOLoop.current().spawn_callback(
        #     self._stats
        # )

    # TODO(e-carlin): If IoLoop.spawn_callback(self._stats) is deleted then
    # this can be deleted too.
    async def _stats(self):
        import tornado.gen
        while True:
            pkdp('====================================')
            pkdp('AGENT_ID={}', self.agent_id)
            pkdp('agent_started={}', self.agent_started())
            pkdp('running_data_jobs={}', self.running_data_jobs)
            pkdp('requests={}', self.requests)
            pkdp('====================================')
            await tornado.gen.sleep(2)

    def start_agent(self, request):
        pkdlog('agent_id={}', self.agent_id)
        if self._agent_starting:
            return
        self._agent_starting = True
        self.resources[self.resource_class].slots.in_use += 1
        self._agent.start(self._on_agent_start_error)

    def kill_agent(self):
        self.resources[self.resource_class].slots.in_use -= 1
        self._agent.kill()
        self._message_handler = None
        self.message_handler_set.clear()

    def _on_agent_start_error(self, returncode):
        pkdlog('agent={} exited with returncode={}', self.agent_id, returncode)
        self.resources[self.resource_class].slots.in_use -= 1
        for r in self.requests:
            assert not r.request_reply_was_sent.is_set(), \
                '{}: should not have been replied to'.format(r)
            r.reply_error()
        
    def set_message_handler(self, message_handler):
        self._agent.agent_started = True
        self._message_handler = message_handler
        self.message_handler_set.set()
        # TODO(e-carlin): Does this make sense? Added to the object so we can
        # call run scheduler on on_close()
        message_handler._resource_class = self.resource_class
        message_handler._driver_class = type(self)


class _LocalAgent():
    def __init__(self, agent_id):
        self.agent_started = False
        self._agent_id = agent_id
        self._agent_process = None
        self._agent_start_attempts = 0
        self._max_agent_start_attempts = 2
        self._agent_kill_requested = False

    def start(self, agent_start_error_callback):
        # TODO(e-carlin): Should this be done in a spawn_callback so we don't hold
        # up the thread?
        pkdlog('agent_id={}', self._agent_id)
        self._agent_start_attempts += 1
        # TODO(e-carlin): Make this more robust. Ex handle failures,
        # monitor the process, be able to kill it
        env = dict(os.environ)
        env['PYENV_VERSION'] = 'py3'
        env['SIREPO_PKCLI_JOB_AGENT_AGENT_ID'] = self._agent_id
        env['SIREPO_PKCLI_JOB_AGENT_JOB_SERVER_WS_URI'] = cfg.job_server_ws_uri
        self._agent_process = tornado.process.Subprocess(
            [
                'pyenv',
                'exec',
                'sirepo',
                'job_agent',
                'start',
            ],
            env=env,
        )
        self._agent_process.set_exit_callback(
            functools.partial(
                self._on_agent_exit, agent_start_error_callback,
            )
        )

    def _on_agent_exit(self, agent_start_error_callback, returncode):
        pkdc('returncode={}', returncode)
        self.agent_started = False
        self._agent_process = None
        if not self._agent_kill_requested and returncode != 0:
            if self._agent_start_attempts >= self._max_agent_start_attempts:
                agent_start_error_callback(returncode)
            else:
                # TODO(e-carlin): look at runner/__init__.py:203
                self.start(agent_start_error_callback)

    def kill(self):
        pkdc('agent_id={}', self._agent_id)
        # TODO(e-carlin): More error handling. If terminate doesn't work
        # we need to go to kill
        # TODO(e-carlin): What happens when an exception is thrown?
        self._agent_kill_requested = True
        self.agent_started = False
        self._agent_process.proc.terminate()
        self._agent_process.proc.wait()
