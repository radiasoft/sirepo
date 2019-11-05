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


#: skip all tests in this model (pytestmark is magic)
pytestmark = pytest.mark.skipif(
    ':job_test:' in ':' + os.environ.get('SIREPO_PYTEST_SKIP', '') + ':',
    reason="SIREPO_PYTEST_SKIP",
)

def test_runStatus():
    py3_env, fc = _env_setup()
    from pykern import pkunit
    from pykern.pkdebug import pkdc, pkdp, pkdlog
    from sirepo import job

    job_supervisor = None
    try:
        job_supervisor = _start_job_supervisor(py3_env)
        fc.get('/myapp')
        data = fc.sr_post(
            'listSimulations',
            {'simulationType': 'myapp',
             'search': {'simulationName': 'heightWeightReport'}},
        )
        data = data[0].simulation
        data = fc.sr_get_json(
            'simulationData',
            params=dict(
                pretty='1',
                simulation_id=data.simulationId,
                simulation_type='myapp',
            ),
        )
        run = fc.sr_post(
            'runStatus',
            dict(
                report='heightWeightReport',
                simulationId=data.models.simulation.simulationId,
                simulationType=data.simulationType,
                computeJobHash='fakeHash',
            ),
        )
        assert run.state == job.MISSING
    finally:
        if job_supervisor:
            job_supervisor.terminate()
            job_supervisor.wait()


def xtest_runSimulation():
    py3_env, fc = _env_setup()
    from pykern import pkunit
    from sirepo import job
    import time

    job_supervisor = None
    try:
        job_supervisor = _start_job_superzvisor(py3_env)
        fc.get('/myapp')
        data = fc.sr_post(
            'listSimulations',
            {'simulationType': 'myapp',
             'search': {'simulation.name': 'heightWeightReport'}},
        )
        data = data[0].simulation
        data = fc.sr_get_json(
            'simulationData',
            params=dict(
                pretty='1',
                simulation_id=data.simulationId,
                simulation_type='myapp',
            ),
        )
        run = fc.sr_post(
            'runSimulation',
            dict(
                forceRun=False,
                models=data.models,
                report='heightWeightReport',
                simulationId=data.models.simulation.simulationId,
                simulationType=data.simulationType,
            ),
        )
        for _ in range(10):
            assert run.state != 'error'
            if run.state == 'completed':
                break
            time.sleep(1)
            run = fc.sr_post(
                'runStatus',
                run.nextRequest
            )
        else:
            pkunit.pkfail('runStatus: failed to complete: {}', run)
        # Just double-check it actually worked
        assert u'plots' in run
    finally:
        if job_supervisor:
            job_supervisor.terminate()
            job_supervisor.wait()


def xtest_cancel_long_running_job():
    py3_env, fc = _env_setup()
    from pykern.pkdebug import pkdc, pkdp, pkdlog
    from pykern import pkunit

    job_supervisor = None
    try:
        job_supervisor = _start_job_supervisor(py3_env)
        fc.get('/myapp')
        data = fc.sr_post(
            'listSimulations',
            {'simulationType': 'myapp',
             'search': {'simulationName': 'heightWeightReport'}},
        )
        data = data[0].simulation
        data = fc.sr_get_json(
            'simulationData',
            params=dict(
                pretty='1',
                simulation_id=data.simulationId,
                simulation_type='myapp',
            ),
        )
        data.models.simulation.name = 'srunit_long_run'
        run = fc.sr_post(
            'runSimulation',
            dict(
                forceRun=False,
                models=data.models,
                report='heightWeightReport',
                simulationId=data.models.simulation.simulationId,
                simulationType=data.simulationType,
            ),
        )

        run = fc.sr_post(
            'runStatus',
            run.nextRequest
        )
        assert run.state == 'running'

        run = fc.sr_post(
            'runCancel',
            dict(
                models=data.models,
                report='heightWeightReport',
                simulationId=data.models.simulation.simulationId,
                simulationType=data.simulationType,
            )
        )
        assert run.state == 'canceled'

        run = fc.sr_post(
            'runStatus',
            # TODO(e-carlin): What actually needs to be in this dict? I just
            # copied from runSimulation
            dict(
                models=data.models,
                report='heightWeightReport',
                simulationId=data.models.simulation.simulationId,
                simulationType=data.simulationType,
            ),
        )
        assert run.state == 'canceled'
    finally:
        if job_supervisor:
            job_supervisor.terminate()
            job_supervisor.wait()


# TODO(e-carlin): pytest is sync but this test need to be run in a async manner
def xtest_one_job_running_at_a_time():
    py3_env, fc = _env_setup()
    from pykern import pkunit

    try:
        job_supervisor = _start_job_supervisor(py3_env)
        fc.get('/myapp')
        data = fc.sr_post(
            'listSimulations',
            {'simulationType': 'myapp',
             'search': {'simulationName': 'heightWeightReport'}},
        )
        data = data[0].simulation
        data = fc.sr_get_json(
            'simulationData',
            params=dict(
                pretty='1',
                simulation_id=data.simulationId,
                simulation_type='myapp',
            ),
        )
        data.models.simulation.name = 'srunit_long_run'
        first_job = fc.sr_post(
            'runSimulation',
            dict(
                forceRun=False,
                models=data.models,
                report='heightWeightReport',
                simulationId=data.models.simulation.simulationId,
                simulationType=data.simulationType,
            ),
        )

        first_job = fc.sr_post(
            'runStatus',
            first_job.nextRequest
        )
        assert first_job.state == 'running'

        data.models.simulation.name = 'Scooby Doo'
        data.models.dog.gender = 'female'
        # TODO(e-carlin): This blocks. Ideally we should run this in something
        # like spawn_callback(). Then call runStatus for second_job see that it
        # is pending. Then call runCancel for first_job. Then call runStatus for
        # the second_job and see that it's state is now running.
        # second_job = fc.sr_post(
        #     'runSimulation',
        #     dict(
        #         forceRun=False,
        #         models=data.models,
        #         report='heightWeightReport',
        #         simulationId=data.models.simulation.simulationId,
        #         simulationType=data.simulationType,
        #     ),
        # )
        # second_job = fc.sr_post(
        #     'runStatus',
        #     second_job.nextRequest
        # )
        # assert second_job.state == 'pending'
    finally:
        job_supervisor.terminate()
        job_supervisor.wait()


def _env_setup():
    """Check if the py3 environment is set up properly"""
    import os
    import subprocess
    # DO NOT import pykern or sirepo to avoid pkconfig init too early

    new_cfg = {
        'PYKERN_PKDEBUG_OUTPUT': '/dev/tty',
        'PYKERN_PKDEBUG_CONTROL': 'job',
        'PYKERN_PKDEBUG_WANT_PID_TIME': '1',
        'SIREPO_FEATURE_CONFIG_JOB_SUPERVISOR': '1',
        'PYTHONUNBUFFERED': '1',
    }
    res = dict()
    for k, v in os.environ.items():
        if ('PYENV' in k or 'PYTHON' in k):
            continue
        if k in ('PATH', 'LD_LIBRARY_PATH'):
            v2 = []
            for x in v.split(':'):
                if x and 'py2' not in x:
                    v2.append(x)
            v = ':'.join(v2)
        res[k] = v
    res['PYENV_VERSION'] = 'py3'
    res.update(new_cfg)

    try:
        out = subprocess.check_output(
            ['pyenv', 'which', 'sirepo'],
            env=res,
            stderr=subprocess.STDOUT,
        )
    except subprocess.CalledProcessError as e:
        out = e.output

    assert '/py3/bin/sirepo' in out, \
        'expecting sirepo in a py3: {}'.format(out)
    try:
        out = subprocess.check_output(
            ['pyenv', 'exec', 'sirepo', 'job_supervisor', '--help'],
            env=res,
            stderr=subprocess.STDOUT,
        )
    except subprocess.CalledProcessError as e:
        out = e.output
    assert 'job_supervisor' in out, \
        '"job_supervisor" not in help: {}'.format(out)

    try:
        out = subprocess.check_output(
            ['pyenv', 'exec', 'sirepo', 'job_driver', '--help'],
            env=res,
            stderr=subprocess.STDOUT,
        )
    except subprocess.CalledProcessError as e:
        out = e.output
    assert 'job_driver' in out, \
        'job_driver not in help: {}'.format(out)

    import sirepo.srunit

    fc = sirepo.srunit.flask_client(sim_types='myapp', cfg=new_cfg)
    fc.sr_login_as_guest()
    return (res, fc)


def _server_up(url):
    import requests
    try:
        r = requests.head(url)
        return r.status_code == 405
    except requests.ConnectionError:
        pass


def _start_job_supervisor(env):
    from pykern import pkunit
    from sirepo import srdb
    import subprocess
    import sys
    import os
    import time

    env['SIREPO_SRDB_ROOT'] = str(srdb.root())
    job_supervisor = subprocess.Popen(
        ['pyenv', 'exec', 'sirepo', 'job_supervisor'],
        env=env,
    )
    from sirepo import job
    for _ in range(30):
        if _server_up('http://127.0.0.1:8001/server'):
            break
        time.sleep(0.1)
    else:
        pkunit.pkfail('job server did not start up')
    return job_supervisor
