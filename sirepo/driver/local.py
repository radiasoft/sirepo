# -*- coding: utf-8 -*-
"""TODO(e-carlin): Doc

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkcollections
from pykern import pkconfig
from pykern.pkdebug import pkdp, pkdlog
from sirepo import driver
from sirepo import job
from sirepo import job_scheduler
import os
import sirepo.mpi
import tornado.process


class LocalDriver(driver.DriverBase):
    requests = pkcollections.Dict(
        parallel=[],
        sequential=[],
    )
    resource_manager = pkcollections.Dict(
        # TODO(e-carlin): Take slots from cfg
        parallel=pkcollections.Dict(total_slots=1, slots_in_use=0),
        sequential=pkcollections.Dict(total_slots=1, slots_in_use=0),
    )
    instances = pkcollections.Dict()
    def __init__(self, uid, agent_id, resource_class):
        super(LocalDriver, self).__init__(uid, agent_id, resource_class)

        # TODO(e-carlin): Make this more robust. Ex handle failures,
        # monitor the process, be able to kill it
        env = dict(os.environ)
        env['PYENV_VERSION'] = 'py3'
        env['SIREPO_PKCLI_JOB_AGENT_AGENT_ID'] = self.agent_id
        env['SIREPO_PKCLI_JOB_AGENT_SUPERVISOR_WS_URI'] = cfg.supervisor_ws_uri
        tornado.process.Subprocess(
            [
                'sirepo',
                'job_agent',
                'start',
            ],
            env=env,
        )


cfg = pkconfig.init(
    supervisor_ws_uri=(
        job.cfg.supervisor_ws_uri,
        str,
        'uri to reach the supervisor for websocket connections',
    ),
)
