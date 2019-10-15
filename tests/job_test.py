# -*- coding: utf-8 -*-
"""End to end test of running a job.

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest
import os
import subprocess
import time
from pykern.pkdebug import pkdc, pkdp, pkdlog
from pykern.pkcollections import PKDict

# TODO(e-carlin): Tests that need to be implemented
#   - agent never starts
#   - agent response is bad (ex no req_id)
#   - server_req is malformed
#   - agent starts but we never get an incoming 'read_for_work' message
#   - canceling of requests in the q and running requests
#   - using only the resources that are available
#   - agent sigterm -> sigkill progression
#   - send kill to uknown agent

def test_runStatus():
    py3_env = _env_setup()
    from sirepo import srunit
    from pykern import pkunit
    from sirepo import job

    fc = srunit.flask_client(sim_types='myapp')
    fc.sr_login_as_guest()

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
        nr = PKDict({
            'report': 'heightWeightReport',
            'simulationId': 'zoVkfTWT',
            'simulationType': 'myapp',
            'reportParametersHash': 'cc093c5d2ff817018618f1422b06fb8e'
            })

        run = fc.sr_post(
            'runStatus',
            nr,
        )

        assert run.status == job.Status.MISSING.value
    finally:
        if job_supervisor:
            job_supervisor.terminate()
            job_supervisor.wait()

def test_myapp():
    py3_env = _env_setup()
    from sirepo import srunit
    from pykern import pkunit
    from sirepo import job

    fc = srunit.flask_client(sim_types='myapp')
    fc.sr_login_as_guest()

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
    py3_env = _env_setup()
    from sirepo import srunit
    from pykern import pkunit

    fc = srunit.flask_client(sim_types='myapp')
    fc.sr_login_as_guest()

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
    py3_env = _env_setup()
    from sirepo import srunit
    from pykern import pkunit

    fc = srunit.flask_client(sim_types='myapp')
    fc.sr_login_as_guest()

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


def _assert_py3():
    """Check if the py3 environment is set up properly"""
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

    try:
        out = subprocess.check_output(
            ['pyenv', 'which', 'sirepo'],
            env=res,
            stderr=subprocess.STDOUT,
        )
    except subprocess.CalledProcessError as e:
        out = e.output
    from pykern import pkunit

    pkdlog('out is {}', out)
    pkunit.pkok(
        '/py3/bin/sirepo' in out,
        'expecting sirepo in a py3: {}',
        out,
    )
    try:
        out = subprocess.check_output(
            ['pyenv', 'exec', 'sirepo', 'job_supervisor', '--help'],
            env=res,
            stderr=subprocess.STDOUT,
        )
    except subprocess.CalledProcessError as e:
        out = e.output
    pkunit.pkok(
        'job_supervisor' in out,
        '"job_supervisor" not in help: {}',
        out,
    )

    try:
        out = subprocess.check_output(
            ['pyenv', 'exec', 'sirepo', 'job_driver', '--help'],
            env=res,
            stderr=subprocess.STDOUT,
        )
    except subprocess.CalledProcessError as e:
        out = e.output
    pkunit.pkok(
        'job_driver' in out,
        '"job_driver" not in help: {}',
        out,
    )
    return res


def _env_setup():
    from pykern import pkconfig

    pkconfig.reset_state_for_testing({
        'SIREPO_FEATURE_CONFIG_JOB_SUPERVISOR': '1',
        'PYTHONUNBUFFERED': '1',
    })
    return _assert_py3()


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

    env['SIREPO_SRDB_ROOT'] = str(srdb.root())
    env['PYKERN_PKDEBUG_OUTPUT'] = '/dev/tty'
    env['PYKERN_PKDEBUG_CONTROL'] = 'job|driver'
    env['PYKERN_PKDEBUG_WANT_PID_TIME'] = '1'
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
