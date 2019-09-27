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
                in_use=pkcollections.Dict(),
            )
        ),
        sequential=pkcollections.Dict(
            drivers=[],
            slots=pkcollections.Dict(
                total=cfg.sequential_slots,
                in_use=pkcollections.Dict(),
            )
        ),
    )

    def __init__(self, uid, resource_class):
        super(LocalDriver, self).__init__(uid, resource_class)
        self._agent = _LocalAgent(self.agent_id)

        # TODO(e-carlin): This is used to get stats about drivers as the code
        # is running. Only useful when closely debugging code. Probably delete.
        tornado.ioloop.IOLoop.current().spawn_callback(
            self._stats
        )

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
            pkdp('resources={}', self.resources)
            pkdp('====================================')
            await tornado.gen.sleep(2)

    def start_agent(self, request):
        pkdlog('agent_id={}', self.agent_id)
        if self._agent_starting:
            return
        self._agent_starting = True
        self._agent.start(self._on_agent_error_exit)
        # claim the slot before the agent has actually started so we don't
        # accidentally give away 1 slot to 2 agents
        self.resources[self.resource_class].slots.in_use[self.agent_id] = self

    def kill_agent(self):
        pkdlog('agent_id={}', self.agent_id)
        self._agent.kill()
        self._message_handler = None
        self._message_handler_set.clear()

    def _on_agent_error_exit(self, returncode):
        pkdlog('agent={} exited with returncode={}', self.agent_id, returncode)
        self._set_agent_stopped_state()
        for r in self.requests:
            assert not r.request_reply_was_sent.is_set(), \
                '{}: should not have been replied to'.format(r)
            r.reply_error()
            self.requests.remove(r)
        job_supervisor.run_scheduler(type(self), self.resource_class) # TODO(e-carlin): Is this necessary?

    def _set_agent_stopped_state(self):
        # TODO(e-carlin): This method is a code smell. I just clear out everything
        # so I know we're in a good state. Maybe I should know the actual state
        # of the agent/driver a bit better and only change things that need to
        # be changed?
        self._agent_starting = False
        self._agent.agent_started = False
        self._message_handler = None
        self._message_handler_set.clear()
        # TODO(e-carlin): It is a hack to use pop. We should know more about
        # when an agent is running or not. It is done like this currently 
        # because it is unclear when on_agent_error_exit vs on_ws_close it called
        self.resources[self.resource_class].slots.in_use.pop(self.agent_id, None)
        
    def set_message_handler(self, message_handler):
        if not self._message_handler_set.is_set():
            self._agent_starting = False
            self._agent.agent_started = True
            self._message_handler = message_handler
            self._message_handler_set.set()
            message_handler._driver = self

    def on_ws_close(self):
        pkdlog('agent_id={}', self.agent_id)
        self._set_agent_stopped_state()
        for r in self.requests:
            # TODO(e-carlin): Think more about this. If the kill was requested
            # maybe the jobs are running too long? If the kill wasn't requested
            # maybe the job can't be run and is what is causing the agent to
            # die?
            if r.state == job_supervisor._STATE_RUNNING:
                r.state = job_supervisor._STATE_RUN_PENDING
        job_supervisor.run_scheduler(type(self), self.resource_class)
class _LocalAgent():
    def __init__(self, agent_id):
        self.agent_started = False
        self._agent_id = agent_id
        self._agent_process = None
        self._agent_start_attempts = 0
        self._max_agent_start_attempts = 2
        self._agent_kill_requested = False

    def start(self, agent_error_exit_callback):
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
                self._on_agent_exit, agent_error_exit_callback,
            )
        )

    def _on_agent_exit(self, agent_error_exit_callback, returncode):
        pkdc(
            'agent_id={}, returncode={}, _agent_kill_requested={}, _agent_start_attemtps={}',
            self._agent_id,
            returncode,
            self._agent_kill_requested,
            self._agent_start_attempts,
        )
        self.agent_started = False
        # if we didn't plan this exit
        if not self._agent_kill_requested or returncode != 0:
            if self._agent_start_attempts > self._max_agent_start_attempts:
                agent_error_exit_callback(returncode)
            else:
                # TODO(e-carlin): look at runner/__init__.py:203
                self.start(agent_error_exit_callback)

    def kill(self):
        pkdc('agent_id={}', self._agent_id)
        # TODO(e-carlin): More error handling. If terminate doesn't work
        # we need to go to kill
        # TODO(e-carlin): What happens when an exception is thrown?
        self._agent_kill_requested = True
        self.agent_started = False
        self._agent_process.proc.terminate()
        self._agent_process.proc.wait()
