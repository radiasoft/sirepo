# -*- coding: utf-8 -*-
"""End to end test of running a job.

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest
import os

# TODO(e-carlin): Tests that need to be implemented
#   - agent never starts
#   - agent response is bad (ex no req_id)
#   - server_req is malformed
#   - agent starts but we never get an incoming 'read_for_work' message
#   - canceling of requests in the q and running requests
#   - using only the resources that are available
#   - agent sigterm -> sigkill progression
#   - send kill to uknown agent

def _setup(func):
    def wrapper(*args, **kwargs):
        p = None
        try:
            env, fc = _job_supervisor_setup()

            from pykern.pkdebug import pkdp, pkdlog
            import sirepo.job
            import sirepo.srdb
            import subprocess
            import time
            from pykern.pkcollections import PKDict

            p = subprocess.Popen(
                ['pyenv', 'exec', 'sirepo', 'job_supervisor'],
                env=env,
            )
            for i in range(30):
                r = fc.sr_post('jobSupervisorPing', PKDict(simulationType=fc.SR_SIM_TYPE_DEFAULT))
                if r.state == 'ok':
                    break
                pkdlog(r)
                time.sleep(.1)
            else:
                pkfail('could not connect to {}', sirepo.job.SERVER_PING_ABS_URI)
            fc.sr_login_as_guest()
            func(fc, fc.sr_sim_data())
        finally:
            if p:
                p.terminate()
                p.wait()
    return wrapper


_REPORT = 'heightWeightReport'


@_setup
def test_runCancel(fc, sim_data):
    from pykern import pkunit
    from pykern.pkdebug import pkdc, pkdp, pkdlog
    import time

    sim_data.models.simulation.name = 'srunit_long_run'
    d = fc.sr_post(
        'runSimulation',
        dict(
            forceRun=False,
            models=sim_data.models,
            report=_REPORT,
            simulationId=sim_data.models.simulation.simulationId,
            simulationType=sim_data.simulationType,
        ),
    )
    for _ in range(10):
        assert d.state != 'error'
        if d.state == 'running':
            break
        time.sleep(d.nextRequestSeconds)
        d = fc.sr_post('runStatus', d.nextRequest)
    else:
        pkunit.pkfail('runStatus: failed to start running: {}', d)

    x = d.nextRequest
    d = fc.sr_post(
        'runCancel',
        x,
    )
    assert d.state == 'canceled'
    d = fc.sr_post(
        'runStatus',
        x,
    )
    assert d.state == 'canceled'


@_setup
def test_runSimulation(fc, sim_data):
    from pykern import pkunit
    from pykern.pkdebug import pkdp, pkdlog
    from sirepo import job
    import time

    d = fc.sr_post(
        'runSimulation',
        dict(
            forceRun=False,
            models=sim_data.models,
            report=_REPORT,
            simulationId=sim_data.models.simulation.simulationId,
            simulationType=sim_data.simulationType,
        ),
    )
    for _ in range(10):
        pkdlog(d)
        assert d.state != 'error'
        if d.state == 'completed':
            break
        time.sleep(d.nextRequestSeconds)
        d = fc.sr_post('runStatus', d.nextRequest)
    else:
        pkunit.pkfail('runStatus: failed to complete: {}', d)
    # Just double-check it actually worked
    assert u'plots' in d


def _job_supervisor_setup():
    """"""
    import os
    from pykern.pkcollections import PKDict

    # DO NOT import pykern or sirepo to avoid pkconfig init too early

    cfg = PKDict(
        PYKERN_PKDEBUG_CONTROL=os.environ.get('PYKERN_PKDEBUG_CONTROL', ''),
        PYKERN_PKDEBUG_OUTPUT=os.environ.get('PYKERN_PKDEBUG_OUTPUT', ''),
        PYKERN_PKDEBUG_WANT_PID_TIME='1',
        PYTHONUNBUFFERED='1',
        SIREPO_FEATURE_CONFIG_JOB='1',
    )
    env = dict()
    for k, v in os.environ.items():
        if ('PYENV' in k or 'PYTHON' in k):
            continue
        if k in ('PATH', 'LD_LIBRARY_PATH'):
            v2 = []
            for x in v.split(':'):
                if x and 'py2' not in x:
                    v2.append(x)
            v = ':'.join(v2)
        env[k] = v
    env['PYENV_VERSION'] = 'py3'
    env.update(cfg)

    import sirepo.srunit

    fc = sirepo.srunit.flask_client(cfg=cfg)
    env['SIREPO_SRDB_ROOT'] = str(sirepo.srdb.root())
    _job_supervisor_check(env)
    return (env, fc)


def _job_supervisor_check(env):
    import sirepo.job
    import socket
    import subprocess

    try:
        o = subprocess.check_output(
            ['pyenv', 'exec', 'sirepo', 'job_supervisor', '--help'],
            env=env,
            stderr=subprocess.STDOUT,
        )
    except subprocess.CalledProcessError as e:
        from pykern.pkdebug import pkdlog

        pkdlog('job_supervisor --help exit={} output={}', e.returncode, e.output)
        raise
    assert 'usage: sirepo job_supervisor' in str(o)
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind((sirepo.job.DEFAULT_IP, int(sirepo.job.DEFAULT_PORT)))
    except Exception:
        raise AssertionError(
            'job_supervisor still running on port={}'.format(sirepo.job.DEFAULT_PORT),
        )
    finally:
        s.close()
