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
from pykern.pkdebug import pkdc, pkdp


def test_myapp():
    py3_env = _env_setup()
    from sirepo import srunit
    from pykern import pkunit
    from sirepo import job

    fc = srunit.flask_client(sim_types='myapp')
    fc.sr_login_as_guest()

    try:
        supervisor = _start_supervisor(py3_env)
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
        supervisor.terminate()
        supervisor.wait()


def test_cancel_long_running_job():
    py3_env = _env_setup()
    from sirepo import srunit
    from pykern import pkunit
    from sirepo import job

    fc = srunit.flask_client(sim_types='myapp')
    fc.sr_login_as_guest()

    try:
        supervisor = _start_supervisor(py3_env)
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
        supervisor.terminate()
        supervisor.wait()


# TODO(e-carlin): pytest is async but this test need to be run in a sync manner
def xtest_one_job_running_at_a_time():
    py3_env = _env_setup()
    from sirepo import srunit
    from pykern import pkunit
    from sirepo import job

    fc = srunit.flask_client(sim_types='myapp')
    fc.sr_login_as_guest()

    try:
        supervisor = _start_supervisor(py3_env)
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
        # TODO(e-carlin): This blocks. Ideally we should run this see that the
        # second_job is 'pending' cancel the first job and then see the second
        # job execute
        second_job = fc.sr_post(
            'runSimulation',
            dict(
                forceRun=False,
                models=data.models,
                report='heightWeightReport',
                simulationId=data.models.simulation.simulationId,
                simulationType=data.simulationType,
            ),
        )
        # second_job = fc.sr_post(
        #     'runStatus',
        #     second_job.nextRequest
        # )
        # assert second_job.state == 'pending'
    finally:
        supervisor.terminate()
        supervisor.wait()


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
        'job_supervisor ' in out,
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


def _start_supervisor(env):
    from pykern import pkunit
    from sirepo import srdb
    from sirepo import job

    env['SIREPO_SRDB_ROOT'] = str(srdb.root())
    supervisor = subprocess.Popen(
        ['pyenv', 'exec', 'sirepo', 'job_supervisor', 'start'],
        env=env,
    )
    for _ in range(30):
        if _server_up(job.cfg.supervisor_http_uri):
            break
        time.sleep(0.1)
    else:
        pkunit.pkfail('job supervisor did not start up')
    return supervisor
