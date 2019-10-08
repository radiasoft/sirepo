# -*- coding: utf-8 -*-
"""TODO(e-carlin): Doc

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkcollections
from pykern import pkconfig
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdlog, pkdexc, pkdc
import functools
import os
import sirepo.driver
import tornado.ioloop
import tornado.locks
import tornado.process


_KILL_TIMEOUT_SECS = 3

cfg = None

def init_class():
    # TODO(e-carlin): cfg should be at bottom like in other modules. Except that
    # class LocalDriver needs it which means it has to be declared before it
    global cfg

    cfg = pkconfig.init(
        parallel_slots=(1, int, 'max parallel slots'),
        sequential_slots=(1, int, 'max sequential slots'),
    )
    LocalDriver.resources = PKDict(
        parallel=_Resources(cfg.parallel_slots),
        sequential=_Resources(cfg.sequential_slots),
    )
    return LocalDriver


class LocalDriver(sirepo.driver.DriverBase):
    KIND = 'local'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        assert self.resources
        self._subprocess = None
        self._start_attempts = 0
        self._max_start_attempts = 2
        self.killing = False
        self._terminate_timeout = None
        self._agent_exited = tornado.locks.Event()


        # TODO(e-carlin): This is used to get stats about drivers as the code
        # is running. Only useful when closely debugging code. Delete when stable.
        # tornado.ioloop.IOLoop.current().spawn_callback(
        #     self._stats
        # )

    def __repr__(self):
        return 'agent_id={} status={} running_data_jobs={} requests={} resources={}'.format(
            self.agent_id,
            self._status,
            self.running_data_jobs,
            self.requests,
            self.resources,
        )


    def slots_available(self):
        s = self.resources[self.resource_class].slots
        return len(s.in_use) < s.total

    # TODO(e-carlin): If IoLoop.spawn_callback(self._stats) is deleted then
    # this can be deleted too.
    async def _stats(self):
        import tornado.gen
        while True:
            pkdlog('{}', self)
            await tornado.gen.sleep(cfg.stats_secs)

    def _kill(self):
        assert self._status
        pkdlog('{}', self)
        # TODO(e-carlin): More error handling. If terminate doesn't work
        # we need to go to kill
        # TODO(e-carlin): What happens when an exception is thrown?
        self._status = sirepo.driver.Status.KILLING
        self._kill_timeout = tornado.ioloop.IOLoop.current().call_later(
            _KILL_TIMEOUT_SECS,
            self._subprocess.proc.kill,
        )
        self._subprocess.proc.terminate()

    def _on_exit(self, returncode):
        pkdc(
            '{} returncode={} _agent_start_attemtps={}',
            self,
            returncode,
            self._start_attempts,
        )
        if self._kill_timeout:
            tornado.ioloop.IOLoop.current().remove_timeout(self._kill_timeout)
            self._kill_timeout = None

        # if we didn't plan this exit
        if self._status is sirepo.driver.Status.KILLING:
            return
        if self._start_attempts > self._max_start_attempts:
            self._on_agent_error_exit()
        else:
            # TODO(e-carlin): look at runner/__init__.py:203
#rn restarts definitely need to be delayed
            self._start()

    def _start(self):
        self._status = sirepo.driver.Status.STARTING
        self._start_attempts += 1
        tornado.ioloop.IOLoop.current().spawn_callback(self._start_cb)

    def _start_cb(self):
        pkdlog('agent_id={}', self.agent_id)
        # TODO(e-carlin): Make this more robust. Ex handle failures,
        # monitor the process, be able to kill it
        env = dict(os.environ)
#rn wrap this in job_subprocess()
        env['PYENV_VERSION'] = 'py3'
#        env['PYKERN_PKDEBUG_OUTPUT'] = '/dev/tty'
#        env['PYKERN_PKDEBUG_CONTROL'] = 'job|driver'
#        env['PYKERN_PKDEBUG_WANT_PID_TIME'] = '1'
        env['SIREPO_PKCLI_JOB_AGENT_AGENT_ID'] = self.agent_id
        env['SIREPO_PKCLI_JOB_AGENT_SUPERVISOR_URI'] = self.supervisor_uri
#rn cwd is where? Probably should be a tmp directory
        self._subprocess = tornado.process.Subprocess(
            [
                'pyenv',
                'exec',
                'sirepo',
                'job_agent',
            ],
            env=env,
        )
        self._subprocess.set_exit_callback(self._on_exit)


class _Resources(PKDict):
    def __init__(self, total):
        self.drivers = []
        self.slots = PKDict(
            total=total,
            in_use=PKDict(),
        )
