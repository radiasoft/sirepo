# -*- coding: utf-8 -*-
"""TODO(e-carlin): Doc

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkcollections
from pykern import pkconfig
from pykern.pkdebug import pkdp, pkdlog, pkdexc
from sirepo import driver
from sirepo import job
from sirepo import job_supervisor
import os
import sirepo.mpi
import tornado.process

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

    def start_agent(self):
        pkdlog('agent_id={}', self.agent_id)
        self._agent.start()

    def terminate_agent(self):
        self._agent.terminate()
        self.message_handler = None
        self.message_handler_set.clear()


class _LocalAgent():
    def __init__(self, agent_id):
        self.agent_started = False
        self._agent_id = agent_id
        self._agent_process = None

    def start(self):
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
        self.agent_started = True

    def terminate(self):
        self.agent_started = False
        self._agent_process.proc.terminate()
        self._agent_process.proc.wait()
